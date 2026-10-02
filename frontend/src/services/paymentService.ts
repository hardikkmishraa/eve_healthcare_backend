import api from './api';
import type { PaymentSimulateRequest, PaymentSimulateResponse } from '../types';

export const paymentService = {
  async simulatePayment(data: PaymentSimulateRequest): Promise<PaymentSimulateResponse> {
    const response = await api.post<PaymentSimulateResponse>('/payments/simulate', data);
    return response.data;
  },
};
