import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown } from "lucide-react";

// 模擬市場數據
const mockMarketData = [
  { pair: "BTC/USDT", price: 42500.50, change24h: 3.25, volume24h: "28.5B" },
  { pair: "ETH/USDT", price: 2250.75, change24h: 2.15, volume24h: "15.2B" },
  { pair: "SOL/USDT", price: 145.30, change24h: -1.50, volume24h: "8.3B" },
  { pair: "XRP/USDT", price: 2.85, change24h: 5.75, volume24h: "6.1B" },
  { pair: "ADA/USDT", price: 1.05, change24h: -0.95, volume24h: "4.2B" },
  { pair: "DOGE/USDT", price: 0.38, change24h: 8.50, volume24h: "3.8B" },
];

export default function MarketData() {
  return (
    <div className="space-y-6">
      {/* 頁面標題 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">市場行情</h1>
        <p className="text-muted-foreground mt-2">實時交易對行情與成交量數據</p>
      </div>

      {/* 市場數據表格 */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle>交易對行情</CardTitle>
          <CardDescription>24 小時價格變化與成交量</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-muted-foreground">交易對</TableHead>
                  <TableHead className="text-right text-muted-foreground">當前價格</TableHead>
                  <TableHead className="text-right text-muted-foreground">24h 漲跌</TableHead>
                  <TableHead className="text-right text-muted-foreground">24h 成交量</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockMarketData.map((item) => (
                  <TableRow key={item.pair} className="border-border/50 hover:bg-muted/30">
                    <TableCell className="font-medium">{item.pair}</TableCell>
                    <TableCell className="text-right font-semibold">
                      ${item.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div
                        className={`flex items-center justify-end gap-1 font-semibold ${
                          item.change24h >= 0 ? "text-up" : "text-down"
                        }`}
                      >
                        {item.change24h >= 0 ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        {item.change24h >= 0 ? "+" : ""}
                        {item.change24h.toFixed(2)}%
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">{item.volume24h}</TableCell>
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
