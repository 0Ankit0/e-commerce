import axios from 'axios';
import type { AxiosError } from 'axios';
import type { PrivilegedActionChallengeDetail, StepUpVerificationResponse } from '@/types';

const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (value: unknown) => void; reject: (reason?: unknown) => void }> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null;

      if (!refreshToken) {
        isRefreshing = false;
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${baseURL}/auth/refresh/`, {
          refresh_token: refreshToken,
        }, {
          params: { set_cookie: false },
        });

        const { access, refresh } = response.data;
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', access);
          localStorage.setItem('refresh_token', refresh);
        }
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${access}`;
        processQueue(null, access);
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    const challenge = (error as AxiosError<{ detail?: PrivilegedActionChallengeDetail }>)?.response?.data?.detail;
    if (
      error.response?.status === 403 &&
      challenge?.code === 'OTP_CHALLENGE_REQUIRED' &&
      !originalRequest?._stepUpRetry &&
      typeof window !== 'undefined'
    ) {
      originalRequest._stepUpRetry = true;
      const otpCode = window.prompt('Enter your 6-digit OTP code to continue this admin action:');
      if (!otpCode) {
        return Promise.reject(error);
      }
      try {
        const verifyResponse = await apiClient.post<StepUpVerificationResponse>('/auth/otp/step-up/verify', {
          otp_code: otpCode.trim(),
          action: challenge.action,
        });
        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers['X-Privileged-Auth'] = verifyResponse.data.step_up_token;
        return apiClient(originalRequest);
      } catch (stepUpError) {
        return Promise.reject(stepUpError);
      }
    }

    return Promise.reject(error);
  }
);
