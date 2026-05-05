import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Plus, Settings } from "lucide-react";

// 模擬策略數據
const mockStrategies = [
  {
    id: 1,
    name: "均線交叉策略",
    description: "基於 MA20 和 MA50 的交叉點進行交易",
    enabled: true,
    status: "running",
    pair: "BTC/USDT",
    parameters: { ma_short: 20, ma_long: 50 },
  },
  {
    id: 2,
    name: "RSI 超買超賣策略",
    description: "當 RSI > 70 時賣出，RSI < 30 時買入",
    enabled: true,
    status: "running",
    pair: "ETH/USDT",
    parameters: { rsi_high: 70, rsi_low: 30 },
  },
  {
    id: 3,
    name: "布林帶突破策略",
    description: "價格突破布林帶上下軌時進行交易",
    enabled: false,
    status: "stopped",
    pair: "SOL/USDT",
    parameters: { period: 20, std_dev: 2 },
  },
];

export default function Strategies() {
  return (
    <div className="space-y-6">
      {/* 頁面標題 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">策略管理</h1>
          <p className="text-muted-foreground mt-2">管理和監控自動化交易策略</p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          新增策略
        </Button>
      </div>

      {/* 策略列表 */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle>活躍策略</CardTitle>
          <CardDescription>所有自動化交易策略的配置與狀態</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-muted-foreground">策略名稱</TableHead>
                  <TableHead className="text-muted-foreground">交易對</TableHead>
                  <TableHead className="text-muted-foreground">狀態</TableHead>
                  <TableHead className="text-muted-foreground">啟用</TableHead>
                  <TableHead className="text-right text-muted-foreground">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockStrategies.map((strategy) => (
                  <TableRow key={strategy.id} className="border-border/50 hover:bg-muted/30">
                    <TableCell>
                      <div>
                        <p className="font-medium">{strategy.name}</p>
                        <p className="text-sm text-muted-foreground">{strategy.description}</p>
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{strategy.pair}</TableCell>
                    <TableCell>
                      <Badge
                        variant={strategy.status === "running" ? "default" : "secondary"}
                        className={
                          strategy.status === "running"
                            ? "bg-up text-white"
                            : "bg-muted text-muted-foreground"
                        }
                      >
                        {strategy.status === "running" ? "運行中" : "已停止"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Switch checked={strategy.enabled} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="gap-2">
                        <Settings className="w-4 h-4" />
                        配置
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
