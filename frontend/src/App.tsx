import { Outlet, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { RequireAuth } from "./lib/auth"
import { LoginPage } from "./pages/LoginPage"
import { OverviewPage } from "./pages/OverviewPage"
import { TicketsPage } from "./pages/TicketsPage"
import { TicketDetailPage } from "./pages/TicketDetailPage"
import { NotFoundPage } from "./pages/NotFoundPage"

/**
 * HashRouter is used (in main.tsx) so that deep links keep working when the
 * built app is served by FastAPI's static files, which has no SPA fallback.
 */
function ProtectedLayout() {
  return (
    <RequireAuth>
      <Layout>
        <Outlet />
      </Layout>
    </RequireAuth>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
