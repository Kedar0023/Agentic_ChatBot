import { type RouteConfig, index, route, layout } from "@react-router/dev/routes";

export default [
  index("routes/index.tsx"),

  // Public-only routes (redirect authenticated users to /home)
  layout("routes/public-layout.tsx", [
    route("login", "routes/login.tsx"),
    route("register", "routes/register.tsx"),
  ]),

  // Protected routes (redirect guest users to /login)
  layout("routes/protected-layout.tsx", [
    route("home", "routes/home.tsx"),
  ]),
] satisfies RouteConfig;
