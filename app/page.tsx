import { DashboardProvider } from '@/components/dashboard/dashboard-provider'
import { TopBar } from '@/components/dashboard/top-bar'
import { LeftSidebar } from '@/components/dashboard/left-sidebar'
import { CenterPanel } from '@/components/dashboard/center-panel'
import { RightPanel } from '@/components/dashboard/right-panel'
import { PanelOverlay } from '@/components/dashboard/panel-overlay'
export default function TradingDashboard() {
  return (
    <DashboardProvider>
      <div className="flex h-screen flex-col bg-background text-foreground overflow-hidden">
        <TopBar />
        <div className="flex flex-1 overflow-hidden">
          <LeftSidebar />
          <CenterPanel />
          <RightPanel />
        </div>
        <PanelOverlay />
      </div>
    </DashboardProvider>
  )
}
