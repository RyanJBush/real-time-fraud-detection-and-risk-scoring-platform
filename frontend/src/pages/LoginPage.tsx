import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("analyst@meridian.ai");
  const [password, setPassword] = useState("password123");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (email && password) {
      navigate("/");
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>Meridian AI</h1>
        <p>Secure access to the fraud intelligence platform.</p>
        <label>
          Work email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </label>
        <button type="submit">Sign in</button>
      </form>
    </div>
  );
}
