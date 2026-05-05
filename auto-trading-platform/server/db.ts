import { eq, and, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users, strategies, trades, positions, marketData } from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

// 策略相關查詢
export async function getStrategiesByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(strategies).where(eq(strategies.userId, userId));
}

export async function getStrategyById(id: number) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(strategies).where(eq(strategies.id, id)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// 交易記錄相關查詢
export async function getTradesByUserId(userId: number, limit: number = 50, offset: number = 0) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(trades).where(eq(trades.userId, userId)).limit(limit).offset(offset);
}

export async function getTradeCountByUserId(userId: number) {
  const db = await getDb();
  if (!db) return 0;
  const result = await db.select({ count: sql`COUNT(*)` }).from(trades).where(eq(trades.userId, userId));
  return result[0]?.count as number || 0;
}

// 持倉相關查詢
export async function getPositionsByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(positions).where(eq(positions.userId, userId));
}

export async function getPositionByUserIdAndPair(userId: number, pair: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(positions).where(
    and(eq(positions.userId, userId), eq(positions.pair, pair))
  ).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// 市場數據相關查詢
export async function getMarketDataByPair(pair: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(marketData).where(eq(marketData.pair, pair)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function getAllMarketData() {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(marketData);
}
