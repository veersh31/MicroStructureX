"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Loader2Icon } from "lucide-react"

interface BacktestResult {
  target_quantity: number
  executed_quantity: number
  fill_rate: number
  vwap: number | null
  arrival_price: number | null
  slippage: number
  slippage_bps: number
  num_child_orders: number
  num_fills: number
  mean_spread: number
  realized_volatility: number
}

export function StrategyBacktest() {
  const [strategy, setStrategy] = useState("twap")
  const [side, setSide] = useState("BUY")
  const [quantity, setQuantity] = useState("1000")
  const [duration, setDuration] = useState("60")
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)

  const handleBacktest = async () => {
    setIsRunning(true)
    setResult(null)

    try {
      const response = await fetch("http://localhost:8000/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy_type: strategy,
          target_quantity: Number.parseFloat(quantity),
          side,
          duration_seconds: Number.parseFloat(duration),
          params: {
            num_slices: 10,
            aggression: 0.5,
          },
        }),
      })

      const data = await response.json()
      setResult(data.results)
    } catch (error) {
      console.log("[v0] Backtest failed:", error)
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>Strategy Backtesting</CardTitle>
        <CardDescription>Test execution strategies against synthetic market replay</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="space-y-2">
            <Label htmlFor="strategy">Strategy</Label>
            <Select value={strategy} onValueChange={setStrategy}>
              <SelectTrigger id="strategy">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="twap">TWAP</SelectItem>
                <SelectItem value="posting">Passive Posting</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="side">Side</Label>
            <Select value={side} onValueChange={setSide}>
              <SelectTrigger id="side">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BUY">Buy</SelectItem>
                <SelectItem value="SELL">Sell</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="quantity">Quantity</Label>
            <Input id="quantity" type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="duration">Duration (s)</Label>
            <Input id="duration" type="number" value={duration} onChange={(e) => setDuration(e.target.value)} />
          </div>
        </div>

        <Button onClick={handleBacktest} disabled={isRunning} className="w-full" size="lg">
          {isRunning ? (
            <>
              <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
              Running Backtest...
            </>
          ) : (
            "Run Backtest"
          )}
        </Button>

        {/* Results */}
        {result && (
          <div className="space-y-4 rounded-lg border border-border bg-muted/30 p-6">
            <h3 className="text-lg font-semibold">Backtest Results</h3>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
              <ResultMetric
                label="Fill Rate"
                value={`${(result.fill_rate * 100).toFixed(1)}%`}
                positive={result.fill_rate > 0.95}
              />
              <ResultMetric
                label="Executed Qty"
                value={`${result.executed_quantity.toFixed(0)} / ${result.target_quantity.toFixed(0)}`}
              />
              <ResultMetric label="VWAP" value={result.vwap ? `$${result.vwap.toFixed(2)}` : "N/A"} />
              <ResultMetric
                label="Arrival Price"
                value={result.arrival_price ? `$${result.arrival_price.toFixed(2)}` : "N/A"}
              />
              <ResultMetric
                label="Slippage"
                value={`${result.slippage_bps.toFixed(2)} bps`}
                positive={result.slippage_bps < 5}
              />
              <ResultMetric label="Child Orders" value={result.num_child_orders.toString()} />
              <ResultMetric label="Fills" value={result.num_fills.toString()} />
              <ResultMetric label="Mean Spread" value={`$${result.mean_spread.toFixed(3)}`} />
              <ResultMetric label="Realized Vol" value={`${(result.realized_volatility * 100).toFixed(2)}%`} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ResultMetric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={`mt-1 text-lg font-mono font-semibold ${
          positive === true ? "text-chart-2" : positive === false ? "text-destructive" : ""
        }`}
      >
        {value}
      </div>
    </div>
  )
}
