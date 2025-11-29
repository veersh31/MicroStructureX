"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { OrderBookView } from "@/components/order-book-view"
import { MetricsPanel } from "@/components/metrics-panel"
import { TradeHistory } from "@/components/trade-history"
import { StrategyBacktest } from "@/components/strategy-backtest"
import { ReplayControls } from "@/components/replay-controls"

export default function MarketMicrostructureDashboard() {
  const [replayActive, setReplayActive] = useState(false)

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="mx-auto max-w-[1920px] space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Market Microstructure Simulator</h1>
            <p className="text-muted-foreground">
              Real-time limit order book with FIFO matching & execution strategies
            </p>
          </div>

          <ReplayControls isActive={replayActive} onToggle={() => setReplayActive(!replayActive)} />
        </div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Left: Order Book Visualization */}
          <div className="lg:col-span-2">
            <OrderBookView />
          </div>

          {/* Right: Live Metrics */}
          <div>
            <MetricsPanel />
          </div>
        </div>

        {/* Bottom Tabs: Strategy Backtesting & Trade History */}
        <Tabs defaultValue="backtest" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="backtest">Strategy Backtest</TabsTrigger>
            <TabsTrigger value="trades">Trade History</TabsTrigger>
          </TabsList>

          <TabsContent value="backtest" className="mt-4">
            <StrategyBacktest />
          </TabsContent>

          <TabsContent value="trades" className="mt-4">
            <TradeHistory />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
