import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router";
import { AlertCircle, Eye, EyeOff, User ,Lock, Info } from "lucide-react";

import { HTTPError } from "ky";
import { Google } from "@/components/svgs/google";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ThemeToggle } from "@/components/ThemeToggle";
import { authSchema, type AuthSchema } from "@/lib/zodSchema";
import { api } from "@/lib/kyClient";
import { useAuthStore, type AuthUser } from "@/lib/ZustandStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const loginAction = useAuthStore((state) => state.login);
  const [serverError, setServerError] = useState<string | null>(null);
  const [betaMessage, setBetaMessage] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AuthSchema>({
    resolver: zodResolver(authSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const onSubmit = async (data: AuthSchema) => {
    setServerError(null);
    try {
      const response = await api
        .post("auth/login", {
          json: {
            username: data.username,
            password: data.password,
          },
        })
        .json<{
          message: string;
          userId: string;
          username: string;
          access_token: string;
        }>();

        console.log(response);

      if (response.access_token) {
        const userObj: AuthUser = {
          id: response.userId,
          userId: response.userId,
          username: response.username,
          is_active: true,
        };
        loginAction(userObj, response.access_token);
      }

      navigate("/home");
    } catch (err) {
      if (err instanceof HTTPError) {
        try {
          const errorData = await err.response.json<{ message?: string; detail?: string; error?: string }>();
          const errorMessage =
            errorData.detail || errorData.message || errorData.error || `Error ${err.response.status}: ${err.response.statusText}`;
          setServerError(errorMessage);
        } catch {
          setServerError(`Error ${err.response.status}: ${err.response.statusText}`);
        }
      } else if (err instanceof Error) {
        setServerError(err.message);
      } else {
        setServerError("An unexpected error occurred. Please try again.");
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="absolute top-10 right-10">
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold tracking-tight">
            Welcome back
          </CardTitle>
          <CardDescription>
            Enter your credentials to sign in to your account
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {serverError && (
            <div
              className="flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          {betaMessage && (
            <div
              className="flex items-center gap-2 rounded-md border border-primary/50 bg-primary/10 p-3 text-sm text-primary"
              role="status"
            >
              <Info className="h-4 w-4 shrink-0" />
              <span>
                Google Sign-In is currently in beta/dev. Please log in with a
                username and password.
              </span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="username"
                  placeholder="Enter your username"
                  autoComplete="username"
                  disabled={isSubmitting}
                  className="pl-9"
                  {...register("username")}
                />
              </div>
              {errors.username && (
                <p className="text-xs text-destructive">{errors.username.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  disabled={isSubmitting}
                  className="pl-9 pr-9"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Log in"}
            </Button>
          </form>

          <div className="relative flex items-center gap-4">
            <Separator className="flex-1" />
            <span className="text-xs text-muted-foreground uppercase">or</span>
            <Separator className="flex-1" />
          </div>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => setBetaMessage(true)}
          >
            <Google className="h-5 w-5" />
            Sign in with Google
          </Button>
        </CardContent>

        <CardFooter className="flex justify-center border-t p-4 text-sm text-muted-foreground">
          <span>Don&apos;t have an account?</span>
          <Link
            to="/register"
            className="ml-1 text-primary underline-offset-4 hover:underline"
          >
            Register
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}