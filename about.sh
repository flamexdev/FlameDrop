
#!/data/data/com.termux/files/usr/bin/bash

clear

R='\033[0;31m'
O='\033[0;33m'
W='\033[1;37m'
G='\033[0;32m'
C='\033[0;36m'
D='\033[0m'

printf "${R}"
cat <<'EOF'
  ______ _ameDrop
 |  ____| |       
 | |__  | |       
 |  __| | |       
 | |    | |____   
 |_|    |______|  
EOF
printf "${D}\n"

printf "${W}FLAMEDROP${D} ${C}PROJECT OVERVIEW${D}\n"
printf "${R}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${D}\n\n"

printf "${O}[ ABOUT ]${D}\n"
echo "FlameDrop is a lightweight, self-hosted"
echo "file-sharing service built with Python."
echo "It allows devices to exchange files"
echo "through a web browser over Wi-Fi."
echo

printf "${O}[ HOW IT WORKS ]${D}\n"
echo "1. Start the FlameDrop server."
echo "2. Connect devices to the same network."
echo "3. Open the server address in a browser."
echo "4. Select and transfer files."
echo

printf "${O}[ TECHNOLOGY ]${D}\n"
echo "  • Python       - Backend server"
echo "  • HTTP         - File communication"
echo "  • HTML         - Web interface"
echo "  • JavaScript   - Web interactions"
echo "  • Wi-Fi / LAN  - Network connectivity"
echo

printf "${O}[ PROJECT FILES ]${D}\n"
echo "  flamedrop.py  - Main server"
echo "  page.html     - Web interface"
echo "  images/       - Project images"
echo "  README.md     - Documentation"
echo

printf "${O}[ FEATURES ]${D}\n"
echo "  • Self-hosted file sharing"
echo "  • Browser-based interface"
echo "  • Local network transfers"
echo "  • No third-party file-sharing platform"
echo "  • Lightweight Python implementation"
echo

printf "${R}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${D}\n"
printf "${G}GitHub:${D} https://github.com/flamexdev/FlameDrop\n"
printf "${C}Developer:${D} FlameXDev\n"
printf "${R}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${D}\n"
