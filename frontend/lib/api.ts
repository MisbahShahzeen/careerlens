import axios from "axios";

const API = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});

API.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const authAPI = {
  register: (email: string, password: string) =>
    API.post("/auth/register", { email, password }),

  login: async (email: string, password: string) => {
    const form = new FormData();
    form.append("username", email);
    form.append("password", password);
    const res = await API.post("/auth/login", form);
    localStorage.setItem("access_token", res.data.access_token);
    return res.data;
  },

  logout: () => {
    localStorage.removeItem("access_token");
  },

  isLoggedIn: (): boolean => {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("access_token");
  },
};

export const analysisAPI = {
  analyze: (resumeFile: File, jobDescription: string) => {
    const form = new FormData();
    form.append("resume", resumeFile);
    form.append("job_description", jobDescription);
    return API.post("/analysis/analyze", form);
  },

  getHistory: () => API.get("/analysis/history"),

  getAnalysis: (analysisId: number) =>
    API.get(`/analysis/${analysisId}`),

  getCoverLetter: (analysisId: number) =>
    API.post(`/analysis/cover-letter/${analysisId}`),
  
};

export default API;