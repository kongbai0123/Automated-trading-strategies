import { decimal, int, mysqlEnum, mysqlTable, text, timestamp, varchar, boolean } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  // 帳戶資訊擴展
  balance: decimal("balance", { precision: 18, scale: 8 }).default("0").notNull(),
  totalProfit: decimal("totalProfit", { precision: 18, scale: 8 }).default("0").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * 自動化交易策略表
 */
export const strategies = mysqlTable("strategies", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  description: text("description"),
  enabled: boolean("enabled").default(true).notNull(),
  // 策略參數 (JSON 格式存儲)
  parameters: text("parameters").notNull(), // JSON string
  // 運行狀態
  status: mysqlEnum("status", ["running", "stopped", "error"]).default("stopped").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Strategy = typeof strategies.$inferSelect;
export type InsertStrategy = typeof strategies.$inferInsert;

/**
 * 交易記錄表
 */
export const trades = mysqlTable("trades", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  strategyId: int("strategyId"),
  // 交易對 (如 BTC/USDT)
  pair: varchar("pair", { length: 50 }).notNull(),
  // 交易方向 (buy/sell)
  direction: mysqlEnum("direction", ["buy", "sell"]).notNull(),
  quantity: decimal("quantity", { precision: 18, scale: 8 }).notNull(),
  price: decimal("price", { precision: 18, scale: 8 }).notNull(),
  // 損益 (正數為盈利，負數為虧損)
  profit: decimal("profit", { precision: 18, scale: 8 }).notNull(),
  fee: decimal("fee", { precision: 18, scale: 8 }).default("0").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type Trade = typeof trades.$inferSelect;
export type InsertTrade = typeof trades.$inferInsert;

/**
 * 持倉管理表
 */
export const positions = mysqlTable("positions", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  // 交易對
  pair: varchar("pair", { length: 50 }).notNull(),
  // 持倉量
  quantity: decimal("quantity", { precision: 18, scale: 8 }).notNull(),
  // 平均成本
  averageCost: decimal("averageCost", { precision: 18, scale: 8 }).notNull(),
  // 當前價格
  currentPrice: decimal("currentPrice", { precision: 18, scale: 8 }).notNull(),
  // 浮動損益
  floatingProfit: decimal("floatingProfit", { precision: 18, scale: 8 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Position = typeof positions.$inferSelect;
export type InsertPosition = typeof positions.$inferInsert;

/**
 * 市場行情數據表
 */
export const marketData = mysqlTable("marketData", {
  id: int("id").autoincrement().primaryKey(),
  // 交易對
  pair: varchar("pair", { length: 50 }).notNull().unique(),
  // 當前價格
  price: decimal("price", { precision: 18, scale: 8 }).notNull(),
  // 24小時漲跌幅 (%)
  change24h: decimal("change24h", { precision: 10, scale: 2 }).notNull(),
  // 24小時成交量
  volume24h: decimal("volume24h", { precision: 18, scale: 2 }).notNull(),
  // 最後更新時間
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type MarketData = typeof marketData.$inferSelect;
export type InsertMarketData = typeof marketData.$inferInsert;