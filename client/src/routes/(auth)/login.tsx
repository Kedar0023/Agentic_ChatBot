import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { HTTPError } from "ky";
import { AlertCircle, Eye, EyeOff, User, Lock, Info } from "lucide-react";

import { api } from "#/lib/KyClient";
import { LoginSchema, type LoginFormData } from "#/schemas/auth";
import { Google } from "#/components/ui/svgs/google";
import { Separator } from "#/components/ui/separator";
import { Button } from "#/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "#/components/ui/form";
import { Input } from "#/components/ui/input";
import { ThemeToggle } from "#/components/ThemeToggle";

export const Route = createFileRoute("/(auth)/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [betaMessage, setBetaMessage] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const form = useForm<LoginFormData>({
    resolver: zodResolver(LoginSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const isSubmitting = form.formState.isSubmitting;

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      let res = await api.post("auth/login", {
        json: {
          username: data.username,
          password: data.password,
        },
      });
      console.log(res);
      navigate({ to: "/" });
    } catch (err) {
      if (err instanceof HTTPError) {
        try {
          const errorData = await err.response.json<{
            message?: string;
            detail?: string;
          }>();
          setServerError(
            errorData.detail ||
            errorData.message ||
            "Login failed. Please try again.",
          );
        } catch {
          setServerError(
            `Login failed (${err.response.status}). Please try again.`,
          );
        }
      } else if (err instanceof Error) {
        setServerError(
          "A network error occurred. Please check your connection and try again.",
        );
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
      <Card className="w-full max-w-md shadow-lg ">
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

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <User className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                          {...field}
                          placeholder="Enter your username"
                          autoComplete="username"
                          disabled={isSubmitting}
                          className="pl-9"
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                          {...field}
                          type={showPassword ? "text" : "password"}
                          placeholder="Enter your password"
                          autoComplete="current-password"
                          disabled={isSubmitting}
                          className="pl-9 pr-9"
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
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Signing in..." : "Log in"}
              </Button>
            </form>
          </Form>

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
