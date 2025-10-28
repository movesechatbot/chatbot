import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/home";
import Login from "./pages/login";
import Register from "./pages/register";
import { io } from "socket.io-client";
import { useSelector } from "react-redux";
import SocketContext from "./context/SocketContext";

// base do backend a partir do endpoint, sem /api/v1 e sem espaços/barras extras
const base = (process.env.REACT_APP_API_ENDPOINT || "").trim().replace(/\/+$/, "");
const socketBase = base.replace(/\/api\/v1$/, ""); // remove /api/v1 se existir
const socket = io(socketBase); // ex.: http://localhost:8000

export default function App() {
  // leitura segura do token
  const token =
    useSelector((s) => s?.user?.user?.token) ??
    JSON.parse(localStorage.getItem("token") || "null");

  return (
    <div className="dark">
      <SocketContext.Provider value={socket}>
        <Router>
          <Routes>
            {/* se tem token -> Home, senão -> Login */}
            <Route path="/" element={token ? <Home socket={socket} /> : <Navigate to="/login" replace />} />
            {/* CORREÇÃO: se tem token, redireciona para "/", senão renderiza Login */}
            <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />
            <Route path="/register" element={<Register />} />
            {/* fallback opcional */}
            <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
          </Routes>
        </Router>
      </SocketContext.Provider>
    </div>
  );
}
