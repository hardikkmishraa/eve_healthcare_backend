import api from './api';
import type { AuthResponse, User } from '../types';

export const authService = {
  async signup(data: {
    email: string;
    password: string;
    full_name: string;
    phone_number?: string;
  }): Promise<User> {
    const response = await api.post<User>('/auth/signup', data);
    return response.data;
  },

  async login(data: { email: string; password: string }): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', data);
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};
