import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', backgroundColor: '#020617', color: '#f87171', height: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', fontFamily: 'sans-serif' }}>
          <h1 style={{ fontSize: '20px', marginBottom: '15px', fontWeight: 'bold' }}>حدث خطأ في النظام (React App Crash)</h1>
          <pre style={{ backgroundColor: '#0f172a', padding: '15px', borderRadius: '12px', border: '1px solid #1e293b', color: '#f1f5f9', maxWidth: '90%', overflowX: 'auto', fontSize: '12px', fontFamily: 'monospace' }}>
            {this.state.error?.stack || this.state.error?.toString()}
          </pre>
          <button onClick={() => window.location.href = "/"} style={{ marginTop: '20px', padding: '8px 20px', backgroundColor: '#e11d48', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
            الرجوع إلى لوحة التحكم الرئيسية
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
