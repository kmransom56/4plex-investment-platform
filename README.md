# 🏘️ 4-Plex Investment Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

> **Comprehensive AI-powered platform for discovering, analyzing, and evaluating 4-plex properties in foreclosure across Georgia counties.**

## ✨ Features

- 🔍 **Automated Discovery** - Multi-county foreclosure property detection
- 🤖 **AI Analysis** - CrewAI-powered property evaluation
- 💰 **Investment Scoring** - Comprehensive ROI and risk assessment
- 📊 **Real-time Dashboard** - Material-UI React interface
- 🏦 **Multi-system Integration** - Unified foreclosure + valuation workflow
- 📈 **Advanced Monitoring** - Grafana dashboards and Prometheus metrics

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/4plex-investment-platform.git
cd 4plex-investment-platform

# Copy environment template
cp .env.example .env

# Start the complete platform
./infrastructure/scripts/start-platform.sh
```

**Access the platform:**
- 📊 **Main Dashboard**: http://localhost:11061
- 🔗 **Integration API**: http://localhost:11060
- 📈 **Monitoring**: http://localhost:11062

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React         │    │   Integration    │    │   Foreclosure   │
│   Dashboard     │◄──►│   API Layer      │◄──►│   Research      │
│   (Port 11061)  │    │   (Port 11060)   │    │   (Port 11050)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Valuation     │    │   Databases      │    │   Monitoring    │
│   System        │    │   PostgreSQL     │    │   Grafana +     │
│   (Port 3000)   │    │   Neo4j + Redis  │    │   Prometheus    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 Requirements

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- 8GB+ RAM recommended
- 50GB+ disk space

## 🛠️ Development

```bash
# Development setup
npm install          # Frontend dependencies
pip install -e .     # Backend dependencies

# Run tests
npm test            # Frontend tests
pytest              # Backend tests

# Development servers
npm run dev         # Frontend dev server
python main.py      # Backend dev server
```

## 🎯 Counties Supported

- **Fulton County** - Atlanta metro area
- **DeKalb County** - Eastern Atlanta suburbs  
- **Clayton County** - Southern Atlanta metro
- **Cobb County** - Northwestern suburbs
- **Atlanta City** - Urban core properties

## 📖 Documentation

- [API Documentation](docs/api/)
- [Deployment Guide](docs/deployment/)
- [Development Setup](docs/development/)
- [User Guide](docs/user-guide/)
- [Architecture Overview](docs/architecture/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 **Email**: support@4plex-platform.com
- 💬 **Issues**: [GitHub Issues](../../issues)
- 📚 **Documentation**: [Wiki](../../wiki)

---

**Built with ❤️ for real estate investors**
