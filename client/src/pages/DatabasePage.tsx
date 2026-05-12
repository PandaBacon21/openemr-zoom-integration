import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export default function DatabasePage() {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Box
        sx={{
          px: 3,
          py: 1.5,
          borderBottom: "1px solid",
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
          gap: 1,
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Database Browser
        </Typography>
        <Typography variant="body2" color="text.secondary">
          — OpenEMR (MariaDB) + Zoomly App (Postgres)
        </Typography>
      </Box>
      <Box sx={{ flex: 1, overflow: "hidden" }}>
        <iframe
          src="/admin/db"
          style={{ width: "100%", height: "100%", border: "none" }}
          title="DbGate Database Browser"
        />
      </Box>
    </Box>
  );
}
