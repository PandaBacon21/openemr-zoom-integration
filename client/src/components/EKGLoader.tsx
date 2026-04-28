import { Box } from "@mui/material";

const EKGLoader: React.FC = () => {
  return (
    <Box
      sx={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "rgba(255,255,255,0.85)",
        borderRadius: 2,
        zIndex: 10,
        backdropFilter: "blur(2px)",
      }}
    >
      <svg
        width="200"
        height="60"
        viewBox="0 0 200 60"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M0,30 L30,30 L40,30 L50,5 L60,55 L70,15 L80,30 L100,30 L110,30 L120,30 L130,5 L140,55 L150,15 L160,30 L200,30"
          stroke="#0B5CFF"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          style={{
            strokeDasharray: 400,
            strokeDashoffset: 400,
            animation: "ekg-draw 1.5s ease-in-out infinite",
          }}
        />
        <style>{`
          @keyframes ekg-draw {
            0% { stroke-dashoffset: 400; opacity: 1; }
            70% { stroke-dashoffset: 0; opacity: 1; }
            85% { stroke-dashoffset: 0; opacity: 0; }
            100% { stroke-dashoffset: 400; opacity: 0; }
          }
        `}</style>
      </svg>
      <Box
        sx={{
          mt: 1.5,
          fontSize: "0.8rem",
          color: "primary.main",
          fontWeight: 600,
          letterSpacing: "0.05em",
          animation: "pulse-text 1.5s ease-in-out infinite",
          "@keyframes pulse-text": {
            "0%, 100%": { opacity: 0.5 },
            "50%": { opacity: 1 },
          },
        }}
      >
        Registering...
      </Box>
    </Box>
  );
};

export default EKGLoader;
