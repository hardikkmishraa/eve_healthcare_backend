import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Booking, PaymentSimulateResponse } from '../types';
import { bookingService } from '../services/bookingService';
import { paymentService } from '../services/paymentService';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import {
  CreditCard,
  CheckCircle2,
  XCircle,
  ArrowRight,
  ShieldCheck,
  Clock,
} from 'lucide-react';

export const PaymentPage: React.FC = () => {
  const { bookingId } = useParams<{ bookingId: string }>();

  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Simulation mode selection
  const [forceStatus, setForceStatus] = useState<'SUCCESS' | 'FAILED' | 'RANDOM'>('SUCCESS');
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<PaymentSimulateResponse | null>(null);

  const loadBooking = async () => {
    if (!bookingId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await bookingService.getBookingById(bookingId);
      setBooking(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load booking details.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBooking();
  }, [bookingId]);

  const handlePay = async () => {
    if (!bookingId) return;
    try {
      setProcessing(true);
      setError(null);
      const paymentResponse = await paymentService.simulatePayment({
        booking_id: bookingId,
        force_status: forceStatus,
      });
      setResult(paymentResponse);
      // Reload booking to refresh its status
      await loadBooking();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Payment simulation failed.';
      setError(msg);
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading booking details for payment..." />;
  }

  if (error && !booking) {
    return (
      <div className="max-w-xl mx-auto py-12">
        <ErrorMessage message={error} onRetry={loadBooking} />
        <Link to="/bookings" className="text-sm text-blue-600 hover:underline">
          Return to My Bookings
        </Link>
      </div>
    );
  }

  if (!booking) return null;

  return (
    <div className="max-w-xl mx-auto py-8 space-y-6">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">Payment Simulation</h1>
        <p className="mt-1 text-sm text-slate-600">
          Complete payment for your scheduled diagnostic appointment.
        </p>
      </div>

      {error && <ErrorMessage message={error} />}

      {/* Outcome Banner after submission */}
      {result && (
        <div
          className={`p-5 rounded-lg border flex items-start gap-3 shadow-sm ${
            result.payment_status === 'SUCCESS'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          {result.payment_status === 'SUCCESS' ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
          )}
          <div className="space-y-1">
            <h3 className="font-semibold text-base">
              {result.payment_status === 'SUCCESS'
                ? 'Payment Successful — Booking Confirmed!'
                : 'Payment Declined — Booking Failed'}
            </h3>
            <p className="text-xs">
              Transaction Reference: <span className="font-mono font-bold">{result.transaction_reference}</span>
            </p>
            <p className="text-xs">
              Booking Status:{' '}
              <span className="font-semibold">{result.booking_status}</span>
            </p>
            <div className="pt-2">
              <Link
                to="/bookings"
                className="inline-flex items-center gap-1 text-xs font-semibold underline hover:no-underline"
              >
                View in My Bookings <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Booking Summary Card */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <span className="text-xs font-mono text-slate-500">Booking: {booking.id}</span>
          <StatusBadge status={booking.status} />
        </div>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between py-1">
            <span className="text-slate-500">Scheduled Time</span>
            <span className="font-medium text-slate-900 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              {formatDateTime(booking.appointment_time)}
            </span>
          </div>

          {booking.notes && (
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Patient Notes</span>
              <span className="font-medium text-slate-900 text-right max-w-xs">{booking.notes}</span>
            </div>
          )}

          <div className="flex justify-between items-center pt-3 border-t border-slate-100">
            <span className="text-base font-semibold text-slate-800">Total Payable</span>
            <span className="text-2xl font-bold text-slate-900">
              {formatCurrency(booking.total_amount)}
            </span>
          </div>
        </div>
      </div>

      {/* Payment Action Section */}
      {booking.status === 'PENDING' ? (
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-5">
          <div>
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-blue-600" /> Simulated Gateway Controls
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Select simulation outcome to test backend transaction transitions and notifications:
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setForceStatus('SUCCESS')}
              className={`py-2 px-3 text-xs font-medium rounded-md border text-center transition-colors ${
                forceStatus === 'SUCCESS'
                  ? 'bg-blue-50 border-blue-600 text-blue-700 font-semibold'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              Force SUCCESS
            </button>
            <button
              type="button"
              onClick={() => setForceStatus('FAILED')}
              className={`py-2 px-3 text-xs font-medium rounded-md border text-center transition-colors ${
                forceStatus === 'FAILED'
                  ? 'bg-blue-50 border-blue-600 text-blue-700 font-semibold'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              Force FAILED
            </button>
            <button
              type="button"
              onClick={() => setForceStatus('RANDOM')}
              className={`py-2 px-3 text-xs font-medium rounded-md border text-center transition-colors ${
                forceStatus === 'RANDOM'
                  ? 'bg-blue-50 border-blue-600 text-blue-700 font-semibold'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              Random (80%)
            </button>
          </div>

          <button
            onClick={handlePay}
            disabled={processing}
            className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <CreditCard className="w-4 h-4" />
            {processing ? 'Processing Payment...' : `Simulate Pay ${formatCurrency(booking.total_amount)}`}
          </button>

          <p className="text-center text-[11px] text-slate-400 flex items-center justify-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            Simulated sandbox environment — no actual card charges will be made.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm text-center space-y-3">
          <p className="text-sm text-slate-600">
            This booking is already in{' '}
            <strong className="text-slate-900">{booking.status}</strong> state. No further payment can be initiated.
          </p>
          <Link
            to="/bookings"
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
          >
            Back to My Bookings <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
};
