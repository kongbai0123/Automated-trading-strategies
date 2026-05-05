import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, X } from "lucide-react";

// 模擬持倉數據
const mockPositions = [
  {
    id: 1,
    pair: "BTC/USDT",
    quantity: 0.5,
    averageCost: 41500,
    currentPrice: 42500,
    floatingProfit: 500,
    profitPercent: 1.2,
  },
  {
    id: 2,
    pair: "ETH/USDT",
    quantity: 5,
    averageCost: 2300,
    currentPrice: 2250,
    floatingProfit: -250,
    profitPercent: -2.2,
  },
  {
    id: 3,
    pair: "SOL/USDT",
    quantity: 10,
    averageCost: 140,
    currentPrice: 145,
    floatingProfit: 50,
    profitPercent: 3.6,
  },
  {
    id: 4,
    pair: "XRP/USDT",
    quantity: 100,
    averageCost: 2.80,
    currentPrice: 2.85,
    floatingProfit: 5,
    profitPercent: 1.8,
  },
  {
    id: 5,
    pair: "ADA/USDT",
    quantity: 200,
    averageCost: 1.08,
    currentPrice: 1.05,
    floatingProfit: -6,
    profitPercent: -2.8,
  },
];

export default function Positions() {
  return (
    <div className="space-y-6">
      {/* 頁面標題 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">持倉管理</h1>
        <p className="text-muted-foreground mt-2">管理當前所有持有的交易倉位</p>
      </div>

      {/* 持倉統計 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">總持倉數</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockPositions.length}</div>
            <p className="text-xs text-muted-foreground mt-1">個交易對</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">浮動盈利</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-up">+$299.00</div>
            <p className="text-xs text-up mt-1">+0.8%</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">總投入成本</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$37,380.00</div>
            <p className="text-xs text-muted-foreground mt-1">USD</p>
          </CardContent>
        </Card>
      </div>

      {/* 持倉明細表 */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle>持倉明細</CardTitle>
          <CardDescription>所有當前持有的交易倉位詳情</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-muted-foreground">交易對</TableHead>
                  <TableHead className="text-right text-muted-foreground">持倉量</TableHead>
                  <TableHead className="text-right text-muted-foreground">平均成本</TableHead>
                  <TableHead className="text-right text-muted-foreground">當前價格</TableHead>
                  <TableHead className="text-right text-muted-foreground">浮動損益</TableHead>
                  <TableHead className="text-right text-muted-foreground">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockPositions.map((position) => (
                  <TableRow key={position.id} className="border-border/50 hover:bg-muted/30">
                    <TableCell className="font-medium">{position.pair}</TableCell>
                    <TableCell className="text-right">{position.quantity}</TableCell>
                    <TableCell className="text-right">${position.averageCost.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-semibold">${position.currentPrice.toLocaleString()}</TableCell>
                    <TableCell className="text-right">
                      <div
                        className={`flex items-center justify-end gap-1 font-semibold ${
                          position.floatingProfit >= 0 ? "text-up" : "text-down"
                        }`}
                      >
                        {position.floatingProfit >= 0 ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        {position.floatingProfit >= 0 ? "+" : ""}${position.floatingProfit.toLocaleString()}
                        <span className="text-xs ml-1">({position.profitPercent >= 0 ? "+" : ""}{position.profitPercent}%)</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                        <X className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
