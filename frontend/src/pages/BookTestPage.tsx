import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import type { DiagnosticCentre, CentreTestOffering } from '../types';
import { centreService } from '../services/centreService';
import { bookingService } from '../services/bookingService';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { formatCurrency, isAtLeastOneHourAhead } from '../utils/formatters';
import { Clock, Building2, FlaskConical, ArrowLeft, ShieldCheck } from 'lucide-react';

export const BookTestPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const queryCentreTestId = searchParams.get('centre_test_id');
  const queryCentreName = searchParams.get('centre_name');
  const queryTestName = searchParams.get('test_name');
  const queryPrice = searchParams.get('price');

  // Form states
  const [centres, setCentres] = useState<DiagnosticCentre[]>([]);
  const [selectedCentreId, setSelectedCentreId] = useState<string>('');
  const [offerings, setOfferings] = useState<CentreTestOffering[]>([]);
  const [selectedCentreTestId, setSelectedCentreTestId] = useState<string>(queryCentreTestId || '');
  const [appointmentDateTime, setAppointmentDateTime] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  const [loadingOfferings, setLoadingOfferings] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Set default appointment time to tomorrow 10:00 AM
  useEffect(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    // Format to YYYY-MM-DDTHH:MM
    const localIso = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    setAppointmentDateTime(localIso);
  }, []);

  // Load centres if no preselected offering or if user wants to change
  useEffect(() => {
    const fetchCentres = async () => {
      try {
        const res = await centreService.getCentres({ page: 1, page_size: 50 });
        setCentres(res.results);
      } catch (err) {
        console.error('Failed to load centres', err);
      }
    };
    fetchCentres();
  }, []);

  // When a centre is picked in dropdown, fetch its test offerings
  useEffect(() => {
    if (!selectedCentreId) return;
    const fetchOfferings = async () => {
      try {
        setLoadingOfferings(true);
        const data = await centreService.getCentreTests(selectedCentreId);
        setOfferings(data);
        if (data.length > 0 && !selectedCentreTestId) {
          setSelectedCentreTestId(data[0].id);
        }
      } catch (err) {
        console.error('Failed to load offerings', err);
      } finally {
        setLoadingOfferings(false);
      }
    };
    fetchOfferings();
  }, [selectedCentreId]);

  // Find currently selected offering to display authoritative price
  const currentOffering = offerings.find((o) => o.id === selectedCentreTestId);
  const displayPrice = currentOffering ? currentOffering.price : queryPrice || '0.00';

  // Minimum appointment time: now + 1 hour 5 minutes
  const minDateTime = new Date(Date.now() + 65 * 60 * 1000 - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const testIdToBook = selectedCentreTestId || queryCentreTestId;
    if (!testIdToBook) {
      setError('Please select a diagnostic test and centre to book.');
      return;
    }

    if (!appointmentDateTime) {
      setError('Please select an appointment date and time.');
      return;
    }

    if (!isAtLeastOneHourAhead(appointmentDateTime)) {
      setError('Appointment must be scheduled at least 1 hour in the future.');
      return;
    }

    try {
      setSubmitting(true);
      // Format to ISO 8601 UTC
      const isoAppointment = new Date(appointmentDateTime).toISOString();
      await bookingService.createBooking({
        centre_test_id: testIdToBook,
        appointment_time: isoAppointment,
        notes: notes.trim() || undefined,
      });

      // Redirect to My Bookings dashboard
      navigate('/bookings');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create booking.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8">
      <Link
        to="/centres"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to centres
      </Link>

      <div className="bg-white border border-slate-200 rounded-lg p-6 sm:p-8 shadow-sm">
        <div className="border-b border-slate-100 pb-5 mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Schedule Diagnostic Appointment</h1>
          <p className="mt-1 text-sm text-slate-600">
            Select your preferred time slot. Total fees are server-verified based on the centre's published rate.
          </p>
        </div>

        {error && <ErrorMessage message={error} />}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Selected Test Summary or Centre/Test Selectors */}
          {queryCentreTestId && queryTestName ? (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Test Selection
                </span>
                <Link
                  to="/centres"
                  className="text-xs font-medium text-blue-600 hover:underline"
                >
                  Change Test
                </Link>
              </div>
              <div className="flex items-center gap-2 text-slate-900 font-semibold">
                <FlaskConical className="w-4 h-4 text-blue-600" />
                <span>{queryTestName}</span>
              </div>
              {queryCentreName && (
                <div className="flex items-center gap-2 text-xs text-slate-600">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" />
                  <span>{queryCentreName}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Diagnostic Centre *
                </label>
                <select
                  value={selectedCentreId}
                  onChange={(e) => {
                    setSelectedCentreId(e.target.value);
                    setSelectedCentreTestId('');
                  }}
                  required
                  className="w-full py-2 px-3 text-sm border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">-- Choose a Centre --</option>
                  {centres.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.city})
                    </option>
                  ))}
                </select>
              </div>

              {selectedCentreId && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Available Test *
                  </label>
                  {loadingOfferings ? (
                    <LoadingSpinner message="Fetching tests for this centre..." />
                  ) : (
                    <select
                      value={selectedCentreTestId}
                      onChange={(e) => setSelectedCentreTestId(e.target.value)}
                      required
                      className="w-full py-2 px-3 text-sm border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="">-- Choose a Diagnostic Test --</option>
                      {offerings.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.test.name} — {formatCurrency(item.price)}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Appointment Date and Time */}
          <div>
            <label htmlFor="appointmentTime" className="block text-sm font-medium text-slate-700 mb-1">
              Appointment Date & Time *
            </label>
            <div className="relative">
              <input
                id="appointmentTime"
                type="datetime-local"
                required
                min={minDateTime}
                value={appointmentDateTime}
                onChange={(e) => setAppointmentDateTime(e.target.value)}
                className="w-full py-2 px-3 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <p className="mt-1 text-xs text-slate-500 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              Must be scheduled at least 1 hour in the future.
            </p>
          </div>

          {/* Patient Notes */}
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-slate-700 mb-1">
              Patient Instructions or Medical Notes (Optional)
            </label>
            <textarea
              id="notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Fasting sample required, wheelchair assistance needed..."
              className="w-full py-2 px-3 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Authoritative Price Summary */}
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 block">Total Authoritative Price</span>
              <span className="text-xl font-bold text-slate-900">{formatCurrency(displayPrice)}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 font-medium">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Fixed Lab Fee
            </div>
          </div>

          {/* Submit Action */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors disabled:opacity-50"
            >
              {submitting ? 'Creating Booking...' : 'Proceed to Payment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
