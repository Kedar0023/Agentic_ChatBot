import { createFileRoute } from '@tanstack/react-router'

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signupSchema, type SignupFormData } from "@/schemas/auth";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";

import { api } from '#/lib/KyClient';

export const Route = createFileRoute('/(auth)/register')({
  component: SignupPage,
})

function SignupPage() {
    
  const form = useForm<SignupFormData>({
      resolver: zodResolver(signupSchema),
      defaultValues: {
          username: "",
          password: "",
          confirmPassword: "",
      },
  });

  async function onSubmit(values: SignupFormData) {
      await api.post("/auth/register", {
          json: {
              username: values.username,
              password: values.password,
          },
      });
  }

  return (
      <main className="flex min-h-screen items-center justify-center p-6">
          <div className="w-full max-w-md rounded-lg border p-8">
              <h1 className="mb-6 text-2xl font-bold">
                  Create Account
              </h1>

              <Form {...form}>
                  <form
                      onSubmit={form.handleSubmit(onSubmit)}
                      className="space-y-5"
                  >
                      <FormField
                          control={form.control}
                          name="username"
                          render={({ field }) => (
                              <FormItem>
                                  <FormLabel>Username</FormLabel>
                                  <FormControl>
                                      <Input
                                          placeholder="johndoe"
                                          {...field}
                                      />
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
                                      <Input
                                          type="password"
                                          {...field}
                                      />
                                  </FormControl>
                                  <FormMessage />
                              </FormItem>
                          )}
                      />

                      <FormField
                          control={form.control}
                          name="confirmPassword"
                          render={({ field }) => (
                              <FormItem>
                                  <FormLabel>Confirm Password</FormLabel>
                                  <FormControl>
                                      <Input
                                          type="password"
                                          {...field}
                                      />
                                  </FormControl>
                                  <FormMessage />
                              </FormItem>
                          )}
                      />

                      <Button
                          type="submit"
                          className="w-full"
                          disabled={form.formState.isSubmitting}
                      >
                          {form.formState.isSubmitting
                              ? "Creating account..."
                              : "Sign Up"}
                      </Button>
                  </form>
              </Form>
          </div>
      </main>
  );
}
