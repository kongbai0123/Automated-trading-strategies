import { describe, expect, it } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

type AuthenticatedUser = NonNullable<TrpcContext["user"]>;

function createAuthContext(): TrpcContext {
  const user: AuthenticatedUser = {
    id: 1,
    openId: "test-user",
    email: "test@example.com",
    name: "Test User",
    loginMethod: "manus",
    role: "user",
    createdAt: new Date(),
    updatedAt: new Date(),
    lastSignedIn: new Date(),
  };

  const ctx: TrpcContext = {
    user,
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {} as TrpcContext["res"],
  };

  return ctx;
}

describe("Trading Router", () => {
  it("getAccount returns account information", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.trading.getAccount();

    expect(result).toBeDefined();
    expect(result.balance).toBe(12000);
    expect(result.totalProfit).toBe(2000);
    expect(result.todayProfit).toBe(-150);
    expect(result.positionCount).toBe(5);
  });

  it("getStrategies returns empty array initially", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.trading.getStrategies();

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(0);
  });

  it("updateStrategyEnabled returns success", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.trading.updateStrategyEnabled({
      strategyId: 1,
      enabled: true,
    });

    expect(result.success).toBe(true);
  });

  it("getTrades returns empty array initially", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.trading.getTrades({ limit: 50, offset: 0 });

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(0);
  });

  it("getPositions returns empty array initially", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.trading.getPositions();

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(0);
  });

  it("getMarketData returns empty array initially", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.trading.getMarketData();

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(0);
  });
});
