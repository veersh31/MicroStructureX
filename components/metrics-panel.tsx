"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowUpIcon, ArrowDownIcon, ActivityIcon, TrendingUpIcon } from "lucide-react"

interface Metrics {
  spread: {
    mean: number
    median: number
    volatility: number
  }
  depth: {
    bid: number
    ask: number
    imbalance: number
  }
  order_flow: {
    imbalance: number
    buy_volume: number
    sell_volume: number
  }
  trades: {
    count: number
    volume: number
    vwap: number | null
  }
  volatility: {
    realized: number
  }
}

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch("http://localhost:8000/metrics")
        const data = await response.json()
        if (!data.message) {
          setMetrics(data)
        }
      } catch (error) {
        console.log("[v0] Failed to fetch metrics:", error)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 2000)
    return () => clearInterval(interval)
  }, [])

  if (!metrics) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Market Metrics</CardTitle>
          <CardDescription>Waiting for market activity...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-[400px] items-center justify-center text-sm text-muted-foreground">
            Start replay to generate metrics
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full bg-card">
      <CardHeader>
        <CardTitle>Market Metrics</CardTitle>
        <CardDescription>Real-time microstructure analytics</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Spread Metrics */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Spread Analysis</h3>
          <div className="grid grid-cols-2 gap-3">
            <MetricCard
              label="Mean Spread"
              value={`$${metrics.spread.mean.toFixed(3)}`}
              icon={<ActivityIcon className="h-4 w-4" />}
            />
            <MetricCard
              label="Spread Vol"
              value={`$${metrics.spread.volatility.toFixed(3)}`}
              icon={<TrendingUpIcon className="h-4 w-4" />}
            />
          </div>
        </div>

        {/* Depth Metrics */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Market Depth</h3>
          <div className="space-y-3">
            <MetricCard
              label="Bid Depth"
              value={metrics.depth.bid.toFixed(0)}
              icon={<ArrowUpIcon className="h-4 w-4 text-chart-2" />}
              className="bg-chart-2/5"
            />
            <MetricCard
              label="Ask Depth"
              value={metrics.depth.ask.toFixed(0)}
              icon={<ArrowDownIcon className="h-4 w-4 text-destructive" />}
              className="bg-destructive/5"
            />
            <div className="rounded-lg border border-border p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Depth Imbalance</span>
                <span
                  className={`text-sm font-mono font-semibold ${
                    metrics.depth.imbalance > 0 ? "text-chart-2" : "text-destructive"
                  }`}
                >
                  {(metrics.depth.imbalance * 100).toFixed(1)}%
                </span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full transition-all ${metrics.depth.imbalance > 0 ? "bg-chart-2" : "bg-destructive"}`}
                  style={{ width: `${Math.abs(metrics.depth.imbalance) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Order Flow */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Order Flow</h3>
          <div className="grid grid-cols-2 gap-3">
            <MetricCard
              label="Buy Volume"
              value={metrics.order_flow.buy_volume.toFixed(0)}
              className="bg-chart-2/5 text-chart-2"
            />
            <MetricCard
              label="Sell Volume"
              value={metrics.order_flow.sell_volume.toFixed(0)}
              className="bg-destructive/5 text-destructive"
            />
          </div>
        </div>

        {/* Trade Statistics */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Trade Statistics</h3>
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Trades" value={metrics.trades.count.toString()} />
            <MetricCard label="Volume" value={metrics.trades.volume.toFixed(0)} />
            {metrics.trades.vwap && (
              <MetricCard
                label="VWAP"
                value={`$${metrics.trades.vwap.toFixed(2)}`}
                className="col-span-2 bg-primary/5"
              />
            )}
          </div>
        </div>

        {/* Volatility */}
        <div className="rounded-lg border border-border p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Realized Volatility</span>
            <span className="text-sm font-mono font-semibold">{(metrics.volatility.realized * 100).toFixed(2)}%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function MetricCard({
  label,
  value,
  icon,
  className = "",
}: {
  label: string
  value: string
  icon?: React.ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-lg border border-border p-3 ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        {icon}
      </div>
      <div className="mt-1 text-lg font-mono font-semibold">{value}</div>
    </div>
  )
}
