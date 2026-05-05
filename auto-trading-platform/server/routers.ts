import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router, protectedProcedure } from "./_core/trpc";
import { getDb } from "./db";
import { z } from "zod";

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  // 交易平台相關的 tRPC procedures
  trading: router({
    // 獲取帳戶信息
    getAccount: protectedProcedure.query(async ({ ctx }) => {
      // 此處可以返回帳戶數據，例如 balance, totalProfit 等
      return {
        balance: 12000,
        totalProfit: 2000,
        todayProfit: -150,
        positionCount: 5,
      };
    }),

    // 獲取所有策略
    getStrategies: protectedProcedure.query(async ({ ctx }) => {
      const db = await getDb();
      if (!db) return [];
      // 從資料庫查詢策略
      return [];
    }),

    // 更新策略啟用狀態
    updateStrategyEnabled: protectedProcedure
      .input(z.object({ strategyId: z.number(), enabled: z.boolean() }))
      .mutation(async ({ ctx, input }) => {
        // 更新策略啟用狀態的邏輯
        return { success: true };
      }),

    // 獲取交易記錄
    getTrades: protectedProcedure
      .input(z.object({ limit: z.number().default(50), offset: z.number().default(0) }))
      .query(async ({ ctx, input }) => {
        const db = await getDb();
        if (!db) return [];
        // 從資料庫查詢交易記錄
        return [];
      }),

    // 獲取持倉信息
    getPositions: protectedProcedure.query(async ({ ctx }) => {
      const db = await getDb();
      if (!db) return [];
      // 從資料庫查詢持倉
      return [];
    }),

    // 獲取市場行情
    getMarketData: protectedProcedure.query(async ({ ctx }) => {
      const db = await getDb();
      if (!db) return [];
      // 從資料庫查詢市場行情
      return [];
    }),
  }),
});

export type AppRouter = typeof appRouter;
