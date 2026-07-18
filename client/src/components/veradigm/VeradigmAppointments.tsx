import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Select,
  Snackbar,
  TextField,
  Alert,
} from "@mui/material";
import type {
  VeradigmAppointment,
  VeradigmAppointmentsResponse,
  VeradigmFetcher,
} from "../../api/veradigm";

interface Props {
  fetcher: VeradigmFetcher;
  showHeader?: boolean;
}

type View = "today" | "future" | "past";

// Zoom-design-system-ish tokens (approximated for MUI).
const T = {
  primary: "#0B5CFF",
  primaryText: "#0B5CFF",
  primSubtle: "#EAF0FF",
  primBorder: "#C7D9FF",
  bg: "#FFFFFF",
  border: "#E6E8EC",
  rowBorder: "#F0F1F4",
  fillNeutral: "#EEF1F4",
  hover: "#F7F8FA",
  textStronger: "#16181D",
  textStrong: "#3A3F47",
  textNeutral: "#6B7280",
  iconStrong: "#4B5563",
  shadowSm: "0 1px 3px rgba(16,24,40,.08)",
};

const TODAY_COLS = "30px minmax(150px,1.5fr) 1.1fr 0.8fr 1fr 1.05fr 0.95fr 210px";
const PAST_COLS = "30px minmax(150px,1.4fr) 1.15fr 0.95fr 0.95fr 1fr 1fr 70px";

const toYMD = (dt: Date): string =>
  `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(
    dt.getDate(),
  ).padStart(2, "0")}`;
const parseYMD = (s: string): Date => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const addDays = (dt: Date, n: number): Date => {
  const c = new Date(dt);
  c.setDate(c.getDate() + n);
  return c;
};
const apptDate = (a: VeradigmAppointment): string =>
  a.start_time ? a.start_time.slice(0, 10) : "";
const fmtDateTime = (iso: string | null): string =>
  iso
    ? new Date(iso).toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "—";

// --- inline icons ----------------------------------------------------------

const IconClock = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12L15 13.5" /></svg>
);
const IconCalendar = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3.5" y="4.5" width="17" height="16" rx="2.5" /><path d="M3.5 9H20.5" /><path d="M8 2.5V6" /><path d="M16 2.5V6" /></svg>
);
const IconCheck = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><path d="M8.5 12.3L11 14.8L15.6 9.8" /></svg>
);
const IconSync = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M20 11a8 8 0 0 0-14-4.5L4 9" /><path d="M4 4v5h5" /><path d="M4 13a8 8 0 0 0 14 4.5L20 15" /><path d="M20 20v-5h-5" /></svg>
);
const IconDots = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 2.6A1.3 1.3 0 1 1 8 5.2A1.3 1.3 0 0 1 8 2.6ZM8 6.7A1.3 1.3 0 1 1 8 9.3A1.3 1.3 0 0 1 8 6.7ZM8 10.8A1.3 1.3 0 1 1 8 13.4A1.3 1.3 0 0 1 8 10.8Z" /></svg>
);
const IconMail = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7.5 12 13l8-5.5" /><rect x="3.5" y="5" width="17" height="14" rx="2.5" /></svg>
);
const IconCopy = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="8.5" y="8.5" width="11" height="11" rx="2.5" /><path d="M15.5 8.5V6A2.5 2.5 0 0 0 13 3.5H6A2.5 2.5 0 0 0 3.5 6v7A2.5 2.5 0 0 0 6 15.5h2.5" /></svg>
);
const IconRoom = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="12" rx="2" /><path d="M8 20.5h8" /></svg>
);

// Empty-state illustration (open box) — approximates the reference art.
const EmptyBox = () => (
  <svg width="132" height="112" viewBox="0 0 132 112" fill="none" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="66" cy="98" rx="46" ry="7" fill="#E7ECF5" />
    <path d="M28 55 L66 66 L104 55 L104 86 L66 98 L28 86 Z" fill="#DCE7FB" />
    <path d="M66 66 L104 55 L104 86 L66 98 Z" fill="#B9CDF9" />
    <path d="M28 55 L44 43 L82 43 L104 55 L66 66 Z" fill="#EAF0FF" />
    <path d="M104 55 L82 43 L92 40 L114 52 Z" fill="#C7D9FF" />
    <path d="M28 55 L44 43 L34 40 L18 52 Z" fill="#C7D9FF" />
    <rect x="78" y="12" width="16" height="12" rx="2" transform="rotate(18 78 12)" fill="#FFC64D" />
    <rect x="40" y="20" width="14" height="10" rx="2" transform="rotate(-14 40 20)" fill="#FFD98A" />
    <rect x="60" y="6" width="12" height="9" rx="2" transform="rotate(6 60 6)" fill="#FFC64D" />
  </svg>
);

const STAT_META: { key: View; label: string; icon: React.FC }[] = [
  { key: "today", label: "Today's Appointments", icon: IconClock },
  { key: "future", label: "Future Appointments", icon: IconCalendar },
  { key: "past", label: "Past Appointments This Week", icon: IconCheck },
];

const HeaderCell: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Box sx={{ fontSize: 12, fontWeight: 600, color: T.textNeutral }}>{children}</Box>
);

const VeradigmAppointments: React.FC<Props> = ({ fetcher, showHeader }) => {
  const [resp, setResp] = useState<VeradigmAppointmentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyEid, setBusyEid] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [view, setView] = useState<View>("today");
  const [futureWeek, setFutureWeek] = useState<"this" | "next">("this");
  const [providerId, setProviderId] = useState<string | null>(null);
  const [providerTouched, setProviderTouched] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [menuAppt, setMenuAppt] = useState<VeradigmAppointment | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResp(await fetcher.getAppointments());
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401 && fetcher.onUnauthorized) {
        fetcher.onUnauthorized();
        return;
      }
      setError("Failed to load appointments");
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    load();
  }, [load]);

  // Default the provider filter to the launching provider (EHR) once loaded;
  // don't override a selection the user has made.
  useEffect(() => {
    if (resp && !providerTouched) setProviderId(resp.default_provider_id);
  }, [resp, providerTouched]);

  const bounds = useMemo(() => {
    const todayStr = resp?.today ?? toYMD(new Date());
    const today = parseYMD(todayStr);
    const mondayOffset = (today.getDay() + 6) % 7;
    const thisMonday = addDays(today, -mondayOffset);
    return {
      todayStr,
      lastMondayStr: toYMD(addDays(thisMonday, -7)),
      thisMondayStr: toYMD(thisMonday),
      thisSundayStr: toYMD(addDays(thisMonday, 6)),
      nextMondayStr: toYMD(addDays(thisMonday, 7)),
      nextSundayStr: toYMD(addDays(thisMonday, 13)),
    };
  }, [resp]);

  const all = resp?.appointments ?? [];

  // Full Veradigm-provider directory (from the server) — options for the search.
  const providerOptions = resp?.providers ?? [];

  const matchesProvider = useCallback(
    (a: VeradigmAppointment) => !providerId || a.provider_id === providerId,
    [providerId],
  );

  const counts = useMemo(() => {
    let today = 0, future = 0, past = 0;
    for (const a of all) {
      if (!matchesProvider(a)) continue;
      const d = apptDate(a);
      if (!d) continue;
      if (d === bounds.todayStr) today += 1;
      else if (d > bounds.todayStr) future += 1;
      else if (d >= bounds.lastMondayStr) past += 1;
    }
    return { today, future, past };
  }, [all, bounds, matchesProvider]);

  const visible = useMemo(
    () =>
      all.filter((a) => {
        if (!matchesProvider(a)) return false;
        const d = apptDate(a);
        if (!d) return false;
        if (view === "today") return d === bounds.todayStr;
        if (view === "past") return d >= bounds.lastMondayStr && d < bounds.todayStr;
        return futureWeek === "this"
          ? d > bounds.todayStr && d <= bounds.thisSundayStr
          : d >= bounds.nextMondayStr && d <= bounds.nextSundayStr;
      }),
    [all, view, futureWeek, bounds, matchesProvider],
  );

  const launch = async (appt: VeradigmAppointment, role: "provider" | "patient") => {
    try {
      let startUrl = appt.start_url;
      let joinUrl = appt.join_url;
      if (!appt.has_meeting) {
        setBusyEid(appt.appointment_id);
        const m = await fetcher.createMeeting(appt.appointment_id);
        startUrl = m.start_url;
        joinUrl = m.join_url;
        setResp((prev) =>
          prev
            ? {
                ...prev,
                appointments: prev.appointments.map((a) =>
                  a.appointment_id === appt.appointment_id
                    ? { ...a, has_meeting: true, start_url: startUrl, join_url: joinUrl }
                    : a,
                ),
              }
            : prev,
        );
      }
      const url = role === "provider" ? startUrl : joinUrl;
      if (url) window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      setError("Failed to start the meeting");
    } finally {
      setBusyEid(null);
    }
  };

  const openMenu = (e: React.MouseEvent<HTMLElement>, appt: VeradigmAppointment) => {
    setMenuAnchor(e.currentTarget);
    setMenuAppt(appt);
  };
  const closeMenu = () => {
    setMenuAnchor(null);
    setMenuAppt(null);
  };
  const copyInvite = async () => {
    const url = menuAppt?.join_url;
    if (url) {
      try {
        await navigator.clipboard.writeText(url);
        setToast("Patient invite link copied");
      } catch {
        setToast("Could not copy link");
      }
    } else {
      setToast("No meeting yet — click Start or Join first");
    }
    closeMenu();
  };

  const toggleRow = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  const allVisibleSelected = visible.length > 0 && visible.every((a) => selected.has(a.appointment_id));
  const toggleAll = () =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) visible.forEach((a) => next.delete(a.appointment_id));
      else visible.forEach((a) => next.add(a.appointment_id));
      return next;
    });

  const isPast = view === "past";
  const cols = isPast ? PAST_COLS : TODAY_COLS;
  const tableTitle =
    view === "today" ? "Today's Appointments" : view === "future" ? "Future Appointments" : "Past Appointments";
  const emptyLabel =
    view === "today"
      ? "No appointments for today"
      : view === "past"
        ? "No past appointments this week"
        : "No future appointments";

  const cbSx = { width: 15, height: 15, accentColor: T.primary, cursor: "pointer" } as const;

  return (
    <Box sx={{ width: "100%", color: T.textStrong }}>
      {showHeader && (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
          <Box sx={{ fontWeight: 800, fontSize: 26, color: T.primary, letterSpacing: "-.02em" }}>zoom</Box>
          <Box sx={{ width: 34, height: 34, borderRadius: "50%", bgcolor: T.primary, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13 }}>PZ</Box>
        </Box>
      )}

      {/* stat cards */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3,1fr)" }, gap: "14px", mb: "18px" }}>
        {STAT_META.map(({ key, label, icon: Icon }) => {
          const active = view === key;
          return (
            <Box
              key={key}
              onClick={() => setView(key)}
              sx={{
                display: "flex", alignItems: "center", gap: "14px", p: "18px 20px", borderRadius: "14px", cursor: "pointer",
                border: `1px solid ${active ? T.primary : T.border}`,
                bgcolor: active ? T.primSubtle : T.bg,
                boxShadow: active ? "none" : T.shadowSm,
                transition: "background .12s ease, border-color .12s ease",
              }}
            >
              <Box sx={{ width: 40, height: 40, flex: "none", borderRadius: "11px", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: active ? T.primary : T.fillNeutral, color: active ? "#fff" : T.iconStrong }}>
                <Icon />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Box sx={{ fontSize: 13, fontWeight: 500, color: T.textNeutral }}>{label}</Box>
                <Box sx={{ fontSize: 28, fontWeight: 700, letterSpacing: "-.5px", color: T.textStronger, mt: "2px" }}>{counts[key]}</Box>
              </Box>
            </Box>
          );
        })}
      </Box>

      {/* table card */}
      <Box sx={{ bgcolor: T.bg, border: `1px solid ${T.border}`, borderRadius: "16px", boxShadow: T.shadowSm, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* header: title + provider search + week dropdown (future) + Sync */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, flexWrap: "wrap", p: "16px 22px 14px", borderBottom: `1px solid ${T.border}` }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Box sx={{ width: 30, height: 30, borderRadius: "50%", bgcolor: T.primary, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <IconClock />
            </Box>
            <Box sx={{ fontSize: 16, fontWeight: 700, letterSpacing: "-.3px", color: T.textStronger }}>{tableTitle}</Box>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <Autocomplete
              size="small"
              options={providerOptions}
              getOptionLabel={(o) => `${o.name} (${o.id})`}
              isOptionEqualToValue={(o, v) => o.id === v.id}
              value={providerOptions.find((o) => o.id === providerId) ?? null}
              onChange={(_, v) => { setProviderTouched(true); setProviderId(v?.id ?? null); }}
              sx={{ width: 260 }}
              renderInput={(p) => <TextField {...p} placeholder="Search and select a provider" />}
            />
            {view === "future" && (
              <Select size="small" value={futureWeek} onChange={(e) => setFutureWeek(e.target.value as "this" | "next")} sx={{ minWidth: 140 }}>
                <MenuItem value="this">This Week</MenuItem>
                <MenuItem value="next">Next Week</MenuItem>
              </Select>
            )}
            <Button variant="outlined" size="small" startIcon={<IconSync />} onClick={load} sx={{ textTransform: "none", whiteSpace: "nowrap", color: T.textStrong, borderColor: T.border }}>
              Sync
            </Button>
          </Box>
        </Box>

        {/* column header */}
        <Box sx={{ display: "grid", gridTemplateColumns: cols, gap: "14px", alignItems: "center", p: "11px 22px", borderBottom: `1px solid ${T.border}` }}>
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <input type="checkbox" style={cbSx} checked={allVisibleSelected} onChange={toggleAll} />
          </Box>
          <HeaderCell>Patient Name</HeaderCell>
          <HeaderCell>Appointment Time</HeaderCell>
          {isPast ? (
            <>
              <HeaderCell>Started</HeaderCell>
              <HeaderCell>Ended</HeaderCell>
              <HeaderCell>Patient Joined</HeaderCell>
              <HeaderCell>Patient Left</HeaderCell>
              <HeaderCell>Note</HeaderCell>
            </>
          ) : (
            <>
              <HeaderCell>Physician ID</HeaderCell>
              <HeaderCell>Physician</HeaderCell>
              <HeaderCell>Assigned Rooms</HeaderCell>
              <HeaderCell>Appointment Type</HeaderCell>
              <HeaderCell>Actions</HeaderCell>
            </>
          )}
        </Box>

        {/* body */}
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress size={26} />
          </Box>
        ) : visible.length === 0 ? (
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5, py: 7 }}>
            <EmptyBox />
            <Box sx={{ color: T.textNeutral, fontSize: 14 }}>{emptyLabel}</Box>
          </Box>
        ) : (
          visible.map((appt) => (
            <Box
              key={appt.appointment_id}
              sx={{ display: "grid", gridTemplateColumns: cols, gap: "14px", alignItems: "center", p: "13px 22px", borderBottom: `1px solid ${T.rowBorder}`, fontSize: 13, "&:hover": { bgcolor: T.hover } }}
            >
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <input type="checkbox" style={cbSx} checked={selected.has(appt.appointment_id)} onChange={() => toggleRow(appt.appointment_id)} />
              </Box>
              <Box sx={{ fontWeight: 700, color: T.textStronger, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {appt.patient_name || appt.patient_id}
              </Box>
              <Box sx={{ color: T.textStrong }}>{fmtDateTime(appt.start_time)}</Box>
              {isPast ? (
                <>
                  <Box sx={{ color: T.textNeutral }}>—</Box>
                  <Box sx={{ color: T.textNeutral }}>—</Box>
                  <Box sx={{ color: T.textNeutral }}>—</Box>
                  <Box sx={{ color: T.textNeutral }}>—</Box>
                  <Box sx={{ color: T.textNeutral }}>—</Box>
                </>
              ) : (
                <>
                  <Box sx={{ color: T.textStrong }}>{appt.provider_id}</Box>
                  <Box sx={{ color: T.textStrong }}>{appt.provider_name}</Box>
                  <Box sx={{ color: T.textNeutral }}>Unassigned</Box>
                  <Box sx={{ color: T.textStrong, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{appt.appointment_type || "—"}</Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: "7px" }}>
                    <Box
                      component="button"
                      onClick={() => launch(appt, "provider")}
                      disabled={busyEid === appt.appointment_id}
                      sx={{ height: 30, px: "15px", border: `1px solid ${T.primBorder}`, borderRadius: "8px", bgcolor: T.primSubtle, color: T.primaryText, fontSize: "12.5px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", "&:hover": { bgcolor: "#DEE9FF" }, "&:disabled": { opacity: 0.6, cursor: "default" } }}
                    >
                      Start
                    </Box>
                    <Box
                      component="button"
                      onClick={() => launch(appt, "patient")}
                      disabled={busyEid === appt.appointment_id}
                      sx={{ height: 30, px: "15px", border: `1px solid ${T.border}`, borderRadius: "8px", bgcolor: T.bg, color: T.textStrong, fontSize: "12.5px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", "&:hover": { bgcolor: T.hover }, "&:disabled": { opacity: 0.6, cursor: "default" } }}
                    >
                      Join
                    </Box>
                    <Box
                      component="button"
                      onClick={(e: React.MouseEvent<HTMLElement>) => openMenu(e, appt)}
                      title="More"
                      sx={{ display: "flex", alignItems: "center", justifyContent: "center", width: 28, height: 28, border: "none", borderRadius: "7px", bgcolor: "transparent", color: T.iconStrong, cursor: "pointer", "&:hover": { bgcolor: T.hover } }}
                    >
                      <IconDots />
                    </Box>
                  </Box>
                </>
              )}
            </Box>
          ))
        )}
      </Box>

      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={closeMenu}>
        <MenuItem onClick={() => { setToast("Invite resent"); closeMenu(); }}>
          <ListItemIcon><IconMail /></ListItemIcon>
          <ListItemText>Resend invite</ListItemText>
        </MenuItem>
        <MenuItem onClick={copyInvite}>
          <ListItemIcon><IconCopy /></ListItemIcon>
          <ListItemText>Copy invite</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => { setToast("Zoom Rooms coming soon"); closeMenu(); }}>
          <ListItemIcon><IconRoom /></ListItemIcon>
          <ListItemText>Add Zoom Rooms</ListItemText>
        </MenuItem>
      </Menu>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      )}
      <Snackbar open={Boolean(toast)} autoHideDuration={2500} onClose={() => setToast(null)} message={toast ?? ""} anchorOrigin={{ vertical: "bottom", horizontal: "center" }} />
    </Box>
  );
};

export default VeradigmAppointments;
