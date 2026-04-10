import { DashboardProvider } from '@/components/dashboard/dashboard-provider'
import { TopBar } from '@/components/dashboard/top-bar'
import { LeftSidebar } from '@/components/dashboard/left-sidebar'
import { CenterPanel } from '@/components/dashboard/center-panel'
import { RightPanel } from '@/components/dashboard/right-panel'

export default function TradingDashboard() {
  return (
    <DashboardProvider>
      <div className="flex min-h-screen flex-col bg-background text-foreground">
        <TopBar />
        <div className="flex flex-1 overflow-hidden">
          <LeftSidebar />
          <CenterPanel />
          <RightPanel />
        </div>
      </div>
    </DashboardProvider>
  )
}
