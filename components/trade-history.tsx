"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

export function TradeHistory() {
  // Mock trade data - in production, fetch from API
  const trades = [
    { id: "T1", time: "10:15:23.142", side: "BUY", price: 100.25, quantity: 50, aggressor: "BUY" },
    { id: "T2", time: "10:15:24.231", side: "SELL", price: 100.2, quantity: 75, aggressor: "SELL" },
    { id: "T3", time: "10:15:25.442", side: "BUY", price: 100.28, quantity: 100, aggressor: "BUY" },
  ]

  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>Trade History</CardTitle>
        <CardDescription>Recent executed trades with timestamps</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Trade ID</TableHead>
              <TableHead>Time</TableHead>
              <TableHead>Side</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">Quantity</TableHead>
              <TableHead>Aggressor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {trades.map((trade) => (
              <TableRow key={trade.id}>
                <TableCell className="font-mono text-sm">{trade.id}</TableCell>
                <TableCell className="font-mono text-sm text-muted-foreground">{trade.time}</TableCell>
                <TableCell>
                  <Badge variant={trade.side === "BUY" ? "default" : "destructive"}>{trade.side}</Badge>
                </TableCell>
                <TableCell className="text-right font-mono font-semibold">${trade.price.toFixed(2)}</TableCell>
                <TableCell className="text-right font-mono">{trade.quantity}</TableCell>
                <TableCell>
                  <Badge variant="outline">{trade.aggressor}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
