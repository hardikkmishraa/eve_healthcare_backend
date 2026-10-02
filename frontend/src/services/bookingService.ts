import api from './api';
import type { Booking, PaginatedResponse } from '../types';

export const bookingService = {
  async createBooking(data: {
    centre_test_id: string;
    appointment_time: string;
    notes?: string;
  }): Promise<Booking> {
    const response = await api.post<Booking>('/bookings', data);
    return response.data;
  },

  async getMyBookings(page = 1, page_size = 20): Promise<PaginatedResponse<Booking>> {
    const response = await api.get<PaginatedResponse<Booking>>('/bookings/my', {
      params: { page, page_size },
    });
    return response.data;
  },

  async getBookingById(id: string): Promise<Booking> {
    const response = await api.get<Booking>(`/bookings/${id}`);
    return response.data;
  },

  async cancelBooking(id: string): Promise<Booking> {
    const response = await api.post<Booking>(`/bookings/${id}/cancel`);
    return response.data;
  },
};
