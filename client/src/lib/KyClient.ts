import ky, { type KyInstance } from "ky";

export const api:KyInstance = ky.create({
  prefix: import.meta.env.VITE_API_URL,

  credentials: "include",

  headers: {
    Accept: "application/json",
  },

  // hooks are like middleware 
  hooks: {
    // beforeRequest: [
    //   (request) => {
    //     const token = localStorage.getItem("access_token");

    //     if (token) {
    //       request.headers.set("Authorization", `Bearer ${token}`);
    //     }
    //   },
    // ],

    // afterResponse: [
    //   async (_request, _options, response) => {
    //     // Future: Refresh token logic
    //     return response;
    //   },
    // ],
  },
});