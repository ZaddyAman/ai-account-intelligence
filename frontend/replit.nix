# Replit Configuration
# Use this if deploying the entire app (frontend + backend) on Replit

{ pkgs }: {
  deps = [
    pkgs.nodejs_20
    pkgs.python311
    pkgs.python311Packages.pip
  ];
  
  # For running the app
  env = {
    PYTHONPATH = ".";
  };
}
