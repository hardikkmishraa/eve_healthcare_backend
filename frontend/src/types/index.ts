export type UserRole = 'PATIENT' | 'ADMIN';

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone_number?: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

export interface DiagnosticCentre {
  id: string;
  name: string;
  address: string;
  city: string;
  pincode: string;
  is_active: boolean;
  created_at: string;
}

export interface DiagnosticTest {
  id: string;
  name: string;
  category: string;
  description?: string | null;
  sample_type?: string | null;
  created_at: string;
}

export interface CentreTestOffering {
  id: string;
  centre_id: string;
  test_id: string;
  price: string | number;
  is_available: boolean;
  test: DiagnosticTest;
  created_at: string;
}

export type BookingStatus = 'PENDING' | 'CONFIRMED' | 'FAILED' | 'CANCELLED';

export interface Booking {
  id: string;
  user_id: string;
  centre_test_id: string;
  appointment_time: string;
  total_amount: string | number;
  status: BookingStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  results: T[];
}

export interface PaymentSimulateRequest {
  booking_id: string;
  force_status?: 'SUCCESS' | 'FAILED' | 'RANDOM';
}

export interface PaymentSimulateResponse {
  payment_id: string;
  booking_id: string;
  transaction_reference: string;
  amount: string | number;
  payment_status: 'SUCCESS' | 'FAILED';
  booking_status: string;
}
