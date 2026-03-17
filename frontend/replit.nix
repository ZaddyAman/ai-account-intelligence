# Replit Configuration
# Use this if deploying the entire app (frontend + backend) on Replit

{ pkgs }: {
  deps = [
    pkgs.nodejs_20
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.playwright
    pkgs.chromium
    pkgs.libglib2_0
    pkgs.libnss3
    pkgs.libnspr4
    pkgs.atk1.0_0
    pkgs.at-spi2-core
    pkgs.libdrm2
    pkgs.libdbus_1_3
    pkgs.libxkbcommon0
    pkgs.libxcomposite1
    pkgs.libxdamage1
    pkgs.libxfixes3
    pkgs.libxrandr2
    pkgs.pango
    pkgs.cairo
    pkgs.stdenv.cc.cc
  ];
  
  # For running the app
  env = {
    PYTHONPATH = ".";
  };
}
