import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import { GuestRoute, Layout, ProtectedRoute } from "./components/common";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Profile from "./pages/Profile";
import MyProjects from "./pages/MyProjects";
import ProjectBoard from "./pages/ProjectBoard";
import Tags from "./pages/Tags";
import "./styles.css";

function NotFound() {
  return <h2>404 — Page not found</h2>;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route element={<GuestRoute />}>
              <Route path="login" element={<Login />} />
              <Route path="signup" element={<Signup />} />
            </Route>
            <Route element={<ProtectedRoute />}>
              <Route path="profile" element={<Profile />} />
              <Route path="my-projects" element={<MyProjects />} />
              <Route path="projects/:projectId" element={<ProjectBoard />} />
              <Route path="tags" element={<Tags />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
