import { OptimizeView } from '@/components/optimize/optimize-view'
import { TopBar } from '@/components/dashboard/top-bar'

export default function OptimizePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <TopBar />
      <OptimizeView />
    </div>
  )
}
