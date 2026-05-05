import { useAuth } from "@/_core/hooks/useAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp, TrendingDown, Wallet, BarChart3 } from "lucide-react";

// 模擬數據
const mockAssetData = [
  { date: "1/1", value: 10000 },
  { date: "1/2", value: 10500 },
  { date: "1/3", value: 10200 },
  { date: "1/4", value: 11000 },
  { date: "1/5", value: 10800 },
  { date: "1/6", value: 11500 },
  { date: "1/7", value: 12000 },
];

export default function Dashboard() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-muted-foreground">載入中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 頁面標題 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">儀表板</h1>
        <p className="text-muted-foreground mt-2">歡迎回來，{user?.name || "交易者"}！</p>
      </div>

      {/* 關鍵指標卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 帳戶餘額 */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Wallet className="w-4 h-4" />
              帳戶餘額
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$12,000.00</div>
            <p className="text-xs text-muted-foreground mt-1">USD</p>
          </CardContent>
        </Card>

        {/* 總損益 */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              總損益
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-up">+$2,000.00</div>
            <p className="text-xs text-up mt-1">+20.0%</p>
          </CardContent>
        </Card>

        {/* 今日盈虧 */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              今日盈虧
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-down">-$150.00</div>
            <p className="text-xs text-down mt-1">-1.2%</p>
          </CardContent>
        </Card>

        {/* 持倉數量 */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              持倉數量
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground mt-1">個交易對</p>
          </CardContent>
        </Card>
      </div>

      {/* 資產曲線圖 */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle>資產曲線走勢</CardTitle>
          <CardDescription>過去 7 天的帳戶資產變化</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockAssetData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" stroke="rgba(255,255,255,0.5)" />
              <YAxis stroke="rgba(255,255,255,0.5)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(20, 20, 35, 0.95)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "0.5rem",
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--up)"
                strokeWidth={2}
                dot={{ fill: "var(--up)", r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
