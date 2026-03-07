import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import AuthPage from "./pages/AuthPage";
import { ChatPage } from "./pages/ChatPage";
import { AdminProtectedRoute } from "./admin/components/AdminProtectedRoute";
import AdminCarsPage from "./admin/pages/AdminCarsPage";
import AdminDialogsPage from "./admin/pages/AdminDialogsPage";
import AdminDialogDetailPage from "./admin/pages/AdminDialogDetailPage";
import AdminUsersPage from "./admin/pages/AdminUsersPage";
import AdminUserDialogsPage from "./admin/pages/AdminUserDialogsPage";
import "./App.css";

const queryClient = new QueryClient();

function RootRedirect() {
  const { token, user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!token) return <Navigate to="/login" replace />;
  return <Navigate to={user?.is_admin ? "/admin/cars" : "/chat"} replace />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <div className="App">
            <Routes>
              <Route path="/login" element={<AuthPage />} />
              <Route element={<ProtectedRoute />}>
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/chat/:sessionId" element={<ChatPage />} />
              </Route>

              {/* Старый адрес админ-логина перенаправляем на общий /login */}
              <Route
                path="/admin/login"
                element={<Navigate to="/login" replace />}
              />

              <Route element={<AdminProtectedRoute />}>
                <Route path="/admin" element={<Navigate to="/admin/cars" replace />} />
                <Route path="/admin/cars" element={<AdminCarsPage />} />
                <Route path="/admin/dialogs" element={<AdminDialogsPage />} />
                <Route
                  path="/admin/dialogs/:sessionId"
                  element={<AdminDialogDetailPage />}
                />
                <Route path="/admin/users" element={<AdminUsersPage />} />
                <Route
                  path="/admin/users/:userId/dialogs"
                  element={<AdminUserDialogsPage />}
                />
              </Route>

              <Route path="/" element={<RootRedirect />} />
              <Route path="*" element={<RootRedirect />} />
            </Routes>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
