import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown } from "lucide-react";

// 模擬交易記錄
const mockTrades = [
  {
    id: 1,
    time: "2024-01-15 14:32:45",
    pair: "BTC/USDT",
    direction: "buy",
    quantity: 0.5,
    price: 42500,
    profit: 500,
  },
  {
    id: 2,
    time: "2024-01-15 13:15:20",
    pair: "ETH/USDT",
    direction: "sell",
    quantity: 5,
    price: 2250,
    profit: -150,
  },
  {
    id: 3,
    time: "2024-01-15 11:45:10",
    pair: "SOL/USDT",
    direction: "buy",
    quantity: 10,
    price: 145,
    profit: 300,
  },
  {
    id: 4,
    time: "2024-01-14 16:20:35",
    pair: "BTC/USDT",
    direction: "sell",
    quantity: 0.3,
    price: 42000,
    profit: -200,
  },
  {
    id: 5,
    time: "2024-01-14 10:05:50",
    pair: "XRP/USDT",
    direction: "buy",
    quantity: 100,
    price: 2.85,
    profit: 50,
  },
];

export default function Trades() {
  return (
    <div className="space-y-6">
      {/* 頁面標題 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">交易記錄</h1>
        <p className="text-muted-foreground mt-2">查看所有歷史交易明細</p>
      </div>

      {/* 交易記錄表格 */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle>交易歷史</CardTitle>
          <CardDescription>所有已執行的交易記錄與損益情況</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-muted-foreground">時間</TableHead>
                  <TableHead className="text-muted-foreground">交易對</TableHead>
                  <TableHead className="text-muted-foreground">方向</TableHead>
                  <TableHead className="text-right text-muted-foreground">數量</TableHead>
                  <TableHead className="text-right text-muted-foreground">價格</TableHead>
                  <TableHead className="text-right text-muted-foreground">損益</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockTrades.map((trade) => (
                  <TableRow key={trade.id} className="border-border/50 hover:bg-muted/30">
                    <TableCell className="text-sm text-muted-foreground">{trade.time}</TableCell>
                    <TableCell className="font-medium">{trade.pair}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          trade.direction === "buy"
                            ? "border-up text-up bg-up-light"
                            : "border-down text-down bg-down-light"
                        }
                      >
                        {trade.direction === "buy" ? "買入" : "賣出"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{trade.quantity}</TableCell>
                    <TableCell className="text-right">${trade.price.toLocaleString()}</TableCell>
                    <TableCell className="text-right">
                      <div
                        className={`flex items-center justify-end gap-1 font-semibold ${
                          trade.profit >= 0 ? "text-up" : "text-down"
                        }`}
                      >
                        {trade.profit >= 0 ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        {trade.profit >= 0 ? "+" : ""}${trade.profit.toLocaleString()}
                      </div>
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
