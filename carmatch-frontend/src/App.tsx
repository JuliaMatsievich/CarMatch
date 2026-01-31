import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/ChatPage";
import "./App.css";

const queryClient = new QueryClient();

function RootRedirect() {
  const { token, isLoading } = useAuth();
  if (isLoading) return null;
  return <Navigate to={token ? "/chat" : "/login"} replace />;
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
