"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface PriceLevel {
  price: number
  quantity: number
}

interface OrderBookData {
  bids: PriceLevel[]
  asks: PriceLevel[]
  spread: number | null
  mid_price: number | null
}

export function OrderBookView() {
  const [orderBook, setOrderBook] = useState<OrderBookData>({
    bids: [],
    asks: [],
    spread: null,
    mid_price: null,
  })

  useEffect(() => {
    // Fetch initial snapshot
    fetchSnapshot()

    // Poll for updates every 500ms
    const interval = setInterval(fetchSnapshot, 500)
    return () => clearInterval(interval)
  }, [])

  const fetchSnapshot = async () => {
    try {
      const response = await fetch("http://localhost:8000/orderbook/snapshot?levels=15")
      const data = await response.json()
      setOrderBook({
        bids: data.bids.map(([price, quantity]: [number, number]) => ({ price, quantity })),
        asks: data.asks.map(([price, quantity]: [number, number]) => ({ price, quantity })),
        spread: data.spread,
        mid_price: data.mid_price,
      })
    } catch (error) {
      console.log("[v0] Failed to fetch order book:", error)
    }
  }

  const maxQuantity = Math.max(...orderBook.bids.map((b) => b.quantity), ...orderBook.asks.map((a) => a.quantity), 1)

  return (
    <Card className="h-full bg-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Order Book</CardTitle>
            <CardDescription>Live depth visualization (L2)</CardDescription>
          </div>
          <div className="flex items-center gap-6">
            {orderBook.mid_price && (
              <div className="text-right">
                <div className="text-xs text-muted-foreground">Mid Price</div>
                <div className="text-lg font-mono font-semibold">${orderBook.mid_price.toFixed(2)}</div>
              </div>
            )}
            {orderBook.spread !== null && (
              <div className="text-right">
                <div className="text-xs text-muted-foreground">Spread</div>
                <div className="text-lg font-mono font-semibold text-chart-3">${orderBook.spread.toFixed(3)}</div>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Asks (Sells) - Top to Bottom */}
          <div className="space-y-0.5">
            <div className="mb-2 flex items-center justify-between text-xs font-medium text-muted-foreground">
              <span>ASKS</span>
              <div className="flex gap-12">
                <span>SIZE</span>
                <span>PRICE</span>
              </div>
            </div>

            {orderBook.asks
              .slice(0, 10)
              .reverse()
              .map((ask, idx) => {
                const widthPercent = (ask.quantity / maxQuantity) * 100
                return (
                  <div key={`ask-${idx}`} className="relative h-6 rounded-sm">
                    <div
                      className="absolute right-0 top-0 h-full rounded-sm bg-destructive/10"
                      style={{ width: `${widthPercent}%` }}
                    />
                    <div className="relative flex items-center justify-between px-2 py-1 text-sm font-mono">
                      <span className="text-muted-foreground">{ask.quantity.toFixed(0)}</span>
                      <span className="font-semibold text-destructive">${ask.price.toFixed(2)}</span>
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Mid Price Line */}
          {orderBook.mid_price && (
            <div className="flex items-center justify-center border-y border-border py-2">
              <div className="text-xs font-medium text-muted-foreground">
                — SPREAD: ${orderBook.spread?.toFixed(3)} —
              </div>
            </div>
          )}

          {/* Bids (Buys) - Top to Bottom */}
          <div className="space-y-0.5">
            <div className="mb-2 flex items-center justify-between text-xs font-medium text-muted-foreground">
              <span>BIDS</span>
              <div className="flex gap-12">
                <span>SIZE</span>
                <span>PRICE</span>
              </div>
            </div>

            {orderBook.bids.slice(0, 10).map((bid, idx) => {
              const widthPercent = (bid.quantity / maxQuantity) * 100
              return (
                <div key={`bid-${idx}`} className="relative h-6 rounded-sm">
                  <div
                    className="absolute right-0 top-0 h-full rounded-sm bg-chart-2/20"
                    style={{ width: `${widthPercent}%` }}
                  />
                  <div className="relative flex items-center justify-between px-2 py-1 text-sm font-mono">
                    <span className="text-muted-foreground">{bid.quantity.toFixed(0)}</span>
                    <span className="font-semibold text-chart-2">${bid.price.toFixed(2)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
