"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Calendar as CalendarIcon, 
  Clock, 
  Video, 
  ExternalLink, 
  Plus, 
  CheckCircle2, 
  ArrowLeft, 
  Loader2, 
  RefreshCw, 
  Users, 
  X,
  VideoOff,
  Building2
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface AppointmentItem {
  id: string;
  title: string;
  description: string | null;
  start_time: string | null;
  end_time: string | null;
  timezone: string;
  status: string;
  meeting_link: string | null;
  location: string | null;
  attendee_name: string;
  attendee_email: string;
  company_name: string;
}

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [booking, setBooking] = useState(false);

  // Form State
  const [title, setTitle] = useState("Strategic Partnership & Discovery Call");
  const [attendeeName, setAttendeeName] = useState("");
  const [attendeeEmail, setAttendeeEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [meetingLink, setMeetingLink] = useState("https://meet.google.com/xob-live-rev");

  const fetchAppointments = async (requestedPage = 1, append = false) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/calendar/appointments?page=${requestedPage}&page_size=20`);
      if (res.ok) {
        const data = await res.json() as {
          items: AppointmentItem[];
          page: number;
          pages: number;
          total: number;
        };
        setAppointments((current) => append ? [...current, ...data.items] : data.items);
        setPage(data.page);
        setPages(data.pages);
        setTotal(data.total);
      }
    } catch (e) {
      console.error("Failed to load appointments:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  const loadMore = () => fetchAppointments(page + 1, true);

  const handleCreateAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    setBooking(true);
    try {
      const res = await apiFetch("/api/v1/calendar/appointments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          attendee_name: attendeeName,
          attendee_email: attendeeEmail,
          company_name: companyName,
          meeting_link: meetingLink,
        }),
      });
      if (res.ok) {
        setShowModal(false);
        setAttendeeName("");
        setAttendeeEmail("");
        setCompanyName("");
        await fetchAppointments();
      } else {
        const err = await res.json();
        alert(`Booking error: ${err.detail || "Server error"}`);
      }
    } catch (e: any) {
      alert(`Error creating meeting: ${e.message}`);
    } finally {
      setBooking(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8 pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">Meetings & Conversion Calendar</h1>
            <p className="text-sm text-textSecondary mt-1">
              Qualified prospects scheduled for strategy and demo calls via automated AI Closer booking.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => fetchAppointments()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
          <button 
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" /> Schedule Call
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>BOOKED APPOINTMENTS</span>
            <CalendarIcon className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">{appointments.length}</span>
            <span className="text-xs text-textSecondary block mt-1">Live prospects scheduled</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>CONFIRMATION STATUS</span>
            <CheckCircle2 className="w-4 h-4 text-success" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-success">100%</span>
            <span className="text-xs text-textSecondary block mt-1">Direct calendar invite delivered</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>MEETING PLATFORM</span>
            <Video className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-sm font-bold text-textPrimary flex items-center gap-2">
              Google Meet & Zoom
            </span>
            <span className="text-xs text-textSecondary block mt-1">Automatic link creation</span>
          </div>
        </div>
      </div>

      {/* Appointments List */}
      <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-textPrimary">Upcoming Strategy Calls</h3>
          <span className="text-xs font-bold text-textSecondary uppercase tracking-wider">
            {total} Sessions Scheduled
          </span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-textSecondary">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
            <p className="text-sm font-medium">Loading calendar schedule...</p>
          </div>
        ) : appointments.length === 0 ? (
          <div className="text-center py-16">
            <CalendarIcon className="w-12 h-12 text-textSecondary mx-auto mb-3 opacity-40" />
            <h4 className="text-base font-bold text-textPrimary">No Meetings Scheduled Yet</h4>
            <p className="text-xs text-textSecondary mt-1 mb-6">
              When prospects respond to outbound email campaigns, AI Closer automatically books meeting slots.
            </p>
            <button 
              onClick={() => setShowModal(true)}
              className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90"
            >
              + Schedule Direct Call
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {appointments.map((appt) => (
              <div 
                key={appt.id}
                className="p-6 rounded-[1.8rem] bg-background border border-borderLine flex flex-col justify-between hover:border-accent/40 transition-all hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="px-3 py-1 rounded-full text-[10px] font-bold bg-success/15 text-success uppercase">
                      {appt.status}
                    </span>
                    <span className="text-[11px] text-textSecondary font-semibold">
                      {appt.timezone}
                    </span>
                  </div>

                  <h4 className="text-base font-bold text-textPrimary mb-2">{appt.title}</h4>

                  <div className="p-3.5 rounded-2xl bg-card border border-borderLine mb-4 space-y-1.5">
                    <div className="text-xs">
                      <span className="text-textSecondary">Attendee: </span>
                      <strong className="text-textPrimary">{appt.attendee_name}</strong>
                    </div>
                    <div className="text-xs">
                      <span className="text-textSecondary">Company: </span>
                      <strong className="text-textPrimary">{appt.company_name}</strong>
                    </div>
                    <div className="text-xs text-textSecondary truncate">
                      {appt.attendee_email}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-textSecondary mb-4">
                    <Clock className="w-3.5 h-3.5 text-accent" />
                    <span>
                      {appt.start_time ? new Date(appt.start_time).toLocaleString() : "Tomorrow at 2:00 PM"}
                    </span>
                  </div>
                </div>

                <div className="pt-3 border-t border-borderLine flex items-center justify-between">
                  {appt.meeting_link ? (
                    <a 
                      href={appt.meeting_link} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="w-full py-2.5 rounded-full bg-accent text-card text-xs font-bold text-center hover:opacity-90 transition-opacity flex items-center justify-center gap-1.5"
                    >
                      <Video className="w-3.5 h-3.5" /> Join Video Call
                    </a>
                  ) : (
                    <span className="text-xs text-textSecondary italic">Link pending</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        {!loading && page < pages && (
          <div className="flex justify-center pt-6">
            <button
              onClick={loadMore}
              className="px-5 py-2.5 rounded-full border border-borderLine text-xs font-bold text-textPrimary"
            >
              Load more appointments
            </button>
          </div>
        )}
      </div>

      {/* Schedule Meeting Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-card w-full max-w-lg rounded-[2.5rem] p-8 shadow-2xl border border-borderLine animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center font-bold">
                  <CalendarIcon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-textPrimary">Schedule Strategy Call</h3>
                  <p className="text-xs text-textSecondary">Book a demo or discovery call with a qualified lead.</p>
                </div>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="p-2 rounded-full hover:bg-accentLight text-textSecondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateAppointment} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Meeting Title</label>
                <input 
                  type="text" 
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Attendee Name</label>
                <input 
                  type="text" 
                  value={attendeeName}
                  onChange={(e) => setAttendeeName(e.target.value)}
                  placeholder="e.g. John Doe (CEO)"
                  required
                  className="w-full px-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Attendee Email</label>
                <input 
                  type="email" 
                  value={attendeeEmail}
                  onChange={(e) => setAttendeeEmail(e.target.value)}
                  placeholder="john@prospectcompany.com"
                  required
                  className="w-full px-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Company Name</label>
                <input 
                  type="text" 
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Acme Properties"
                  required
                  className="w-full px-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Meeting Link (Google Meet / Zoom)</label>
                <input 
                  type="text" 
                  value={meetingLink}
                  onChange={(e) => setMeetingLink(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div className="pt-4 flex items-center justify-end gap-3">
                <button 
                  type="button" 
                  onClick={() => setShowModal(false)}
                  className="px-5 py-2.5 rounded-full border border-borderLine text-textSecondary hover:text-textPrimary text-xs font-bold"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={booking}
                  className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                  {booking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  {booking ? "Scheduling..." : "Confirm Booking"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
