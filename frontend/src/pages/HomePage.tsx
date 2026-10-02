import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { DiagnosticCentre, DiagnosticTest } from '../types';
import { centreService } from '../services/centreService';
import { LoadingSpinner } from '../components/LoadingSpinner';
import {
  Building2,
  Calendar,
  CreditCard,
  Search,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

export const HomePage: React.FC = () => {
  const [featuredCentres, setFeaturedCentres] = useState<DiagnosticCentre[]>([]);
  const [popularTests, setPopularTests] = useState<DiagnosticTest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [centresRes, testsRes] = await Promise.all([
          centreService.getCentres({ page: 1, page_size: 4 }),
          centreService.getTests({ page: 1, page_size: 4 }),
        ]);
        setFeaturedCentres(centresRes.results);
        setPopularTests(testsRes.results);
      } catch (err) {
        console.error('Failed to load home data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="space-y-12 py-8">
      {/* Introduction Banner (Clean, Practical, No excessive gradients) */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 sm:p-10 shadow-sm">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100 mb-4">
            <ShieldCheck className="w-3.5 h-3.5" />
            Reliable Diagnostic Network
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 leading-tight">
            Book Diagnostic Tests at Verified Healthcare Centres
          </h1>
          <p className="mt-3 text-base sm:text-lg text-slate-600 leading-relaxed">
            EVE Healthcare connects patients with trusted diagnostic laboratories across major cities.
            Explore authentic lab pricing, select your convenient appointment time, and manage your bookings effortlessly.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/centres"
              className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors"
            >
              Book a Test
              <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
            <Link
              to="/tests"
              className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-md transition-colors"
            >
              Browse All Tests
            </Link>
          </div>
        </div>
      </section>

      {/* 3 Step Workflow */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="w-10 h-10 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
            <Search className="w-5 h-5" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">1. Select a Centre & Test</h3>
          <p className="mt-1 text-sm text-slate-600">
            Compare diagnostic facilities by city, address, and localized test prices.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="w-10 h-10 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
            <Calendar className="w-5 h-5" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">2. Schedule Appointment</h3>
          <p className="mt-1 text-sm text-slate-600">
            Choose a date and time that fits your routine. Server-verified pricing guaranteed.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
          <div className="w-10 h-10 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
            <CreditCard className="w-5 h-5" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">3. Safe Payment Processing</h3>
          <p className="mt-1 text-sm text-slate-600">
            Simulate and complete transactions with guaranteed idempotent webhook processing.
          </p>
        </div>
      </section>

      {/* Featured Diagnostic Centres */}
      <section className="space-y-4">
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Partner Diagnostic Centres</h2>
            <p className="text-sm text-slate-500">Accredited laboratories with certified equipment</p>
          </div>
          <Link
            to="/centres"
            className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            View all centres <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {loading ? (
          <LoadingSpinner message="Loading diagnostic centres..." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {featuredCentres.map((centre) => (
              <div
                key={centre.id}
                className="bg-white border border-slate-200 rounded-lg p-4 flex flex-col justify-between hover:border-slate-300 transition-colors shadow-sm"
              >
                <div>
                  <div className="flex items-center gap-2 text-slate-900 font-semibold text-base mb-1">
                    <Building2 className="w-4 h-4 text-blue-600 shrink-0" />
                    <span className="truncate">{centre.name}</span>
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-2">{centre.address}</p>
                  <p className="mt-2 text-xs font-medium text-slate-700">
                    City: <span className="text-blue-700">{centre.city}</span> ({centre.pincode})
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <Link
                    to={`/centres/${centre.id}`}
                    className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                  >
                    View Tests & Pricing <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Common Diagnostic Tests */}
      <section className="space-y-4">
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Common Diagnostic Tests</h2>
            <p className="text-sm text-slate-500">Routine and specialized pathology & biochemistry profiles</p>
          </div>
          <Link
            to="/tests"
            className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            View all tests <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {loading ? (
          <LoadingSpinner message="Loading tests..." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {popularTests.map((t) => (
              <div
                key={t.id}
                className="bg-white border border-slate-200 rounded-lg p-4 flex flex-col justify-between shadow-sm"
              >
                <div>
                  <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 mb-2">
                    {t.category}
                  </span>
                  <h3 className="font-semibold text-sm text-slate-900 leading-snug">{t.name}</h3>
                  <p className="mt-1 text-xs text-slate-500 line-clamp-2">
                    {t.description || 'Standard clinical diagnostic evaluation.'}
                  </p>
                </div>
                <div className="mt-3 text-xs text-slate-500">
                  Sample: <span className="font-medium text-slate-700">{t.sample_type || 'Blood'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
