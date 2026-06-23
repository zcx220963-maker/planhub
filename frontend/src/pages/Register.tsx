import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Sparkles } from 'lucide-react';
import './Login.css';

const Pupil = ({ size = 12, maxDistance = 5, pupilColor = '#2D2D2D', forceLookX, forceLookY }: {
  size?: number; maxDistance?: number; pupilColor?: string; forceLookX?: number; forceLookY?: number;
}) => {
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const pupilRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => { setMouseX(e.clientX); setMouseY(e.clientY); };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const calculatePupilPosition = () => {
    if (!pupilRef.current) return { x: 0, y: 0 };
    if (forceLookX !== undefined && forceLookY !== undefined) return { x: forceLookX, y: forceLookY };
    const pupil = pupilRef.current.getBoundingClientRect();
    const pupilCenterX = pupil.left + pupil.width / 2;
    const pupilCenterY = pupil.top + pupil.height / 2;
    const deltaX = mouseX - pupilCenterX;
    const deltaY = mouseY - pupilCenterY;
    const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);
    const angle = Math.atan2(deltaY, deltaX);
    return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance };
  };

  const pupilPos = calculatePupilPosition();

  return (
    <div
      ref={pupilRef}
      className="login-pupil"
      style={{ width: `${size}px`, height: `${size}px`, backgroundColor: pupilColor, transform: `translate(${pupilPos.x}px, ${pupilPos.y}px)` }}
    />
  );
};

const EyeBall = ({ size = 48, pupilSize = 16, maxDistance = 10, eyeColor = 'white', pupilColor = '#2D2D2D', isBlinking = false, forceLookX, forceLookY }: {
  size?: number; pupilSize?: number; maxDistance?: number; eyeColor?: string; pupilColor?: string; isBlinking?: boolean; forceLookX?: number; forceLookY?: number;
}) => {
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const eyeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => { setMouseX(e.clientX); setMouseY(e.clientY); };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const calculatePupilPosition = () => {
    if (!eyeRef.current) return { x: 0, y: 0 };
    if (forceLookX !== undefined && forceLookY !== undefined) return { x: forceLookX, y: forceLookY };
    const eye = eyeRef.current.getBoundingClientRect();
    const eyeCenterX = eye.left + eye.width / 2;
    const eyeCenterY = eye.top + eye.height / 2;
    const deltaX = mouseX - eyeCenterX;
    const deltaY = mouseY - eyeCenterY;
    const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);
    const angle = Math.atan2(deltaY, deltaX);
    return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance };
  };

  const pupilPos = calculatePupilPosition();

  return (
    <div
      ref={eyeRef}
      className="login-eyeball"
      style={{ width: `${size}px`, height: isBlinking ? '2px' : `${size}px`, backgroundColor: eyeColor }}
    >
      {!isBlinking && (
        <div
          className="login-eyeball-pupil"
          style={{ width: `${pupilSize}px`, height: `${pupilSize}px`, backgroundColor: pupilColor, transform: `translate(${pupilPos.x}px, ${pupilPos.y}px)` }}
        />
      )}
    </div>
  );
};

const Register: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const [isPurpleBlinking, setIsPurpleBlinking] = useState(false);
  const [isBlackBlinking, setIsBlackBlinking] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false);
  const purpleRef = useRef<HTMLDivElement>(null);
  const blackRef = useRef<HTMLDivElement>(null);
  const yellowRef = useRef<HTMLDivElement>(null);
  const orangeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => { setMouseX(e.clientX); setMouseY(e.clientY); };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const scheduleBlink = () => {
      const t = setTimeout(() => {
        setIsPurpleBlinking(true);
        setTimeout(() => { setIsPurpleBlinking(false); scheduleBlink(); }, 150);
      }, Math.random() * 4000 + 3000);
      return t;
    };
    const timeout = scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    const scheduleBlink = () => {
      const t = setTimeout(() => {
        setIsBlackBlinking(true);
        setTimeout(() => { setIsBlackBlinking(false); scheduleBlink(); }, 150);
      }, Math.random() * 4000 + 3000);
      return t;
    };
    const timeout = scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (isTyping) {
      setIsLookingAtEachOther(true);
      const timer = setTimeout(() => setIsLookingAtEachOther(false), 800);
      return () => clearTimeout(timer);
    } else {
      setIsLookingAtEachOther(false);
    }
  }, [isTyping]);

  const calculatePosition = (ref: React.RefObject<HTMLDivElement | null>) => {
    if (!ref.current) return { faceX: 0, faceY: 0, bodySkew: 0 };
    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 3;
    const deltaX = mouseX - centerX;
    const deltaY = mouseY - centerY;
    return {
      faceX: Math.max(-15, Math.min(15, deltaX / 20)),
      faceY: Math.max(-10, Math.min(10, deltaY / 30)),
      bodySkew: Math.max(-6, Math.min(6, -deltaX / 120)),
    };
  };

  const purplePos = calculatePosition(purpleRef);
  const blackPos = calculatePosition(blackRef);
  const yellowPos = calculatePosition(yellowRef);
  const orangePos = calculatePosition(orangeRef);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    if (username.length < 3) {
      setError('用户名长度必须在3个字符以上');
      return;
    }
    if (!displayName.trim()) {
      setError('显示名称不能为空');
      return;
    }

    setIsLoading(true);
    try {
      await register({ username, displayName, email, password });
      alert('注册成功！请登录');
      navigate('/login');
    } catch {
      setError('注册失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-grid">
        {/* 左侧品牌区 */}
        <div className="login-left-section">
          <div className="login-brand-logo">
            <div className="login-brand-icon">
              <Sparkles className="login-brand-icon-svg" />
            </div>
            <div className="login-brand-info">
              <span className="login-brand-name">PlanHub</span>
              <p className="login-brand-tagline">智能打卡社区平台</p>
            </div>
          </div>

          <div className="login-intro-section">
            <h2 className="login-intro-title">开启你的</h2>
            <h2 className="login-intro-title">计划管理之旅</h2>
            <p className="login-intro-text">Track your goals, achieve your dreams, and build habits that last.</p>
          </div>

          <div className="login-characters-container">
            <div className="login-characters-wrapper">
              {/* 紫色角色 */}
              <div
                ref={purpleRef}
                className="login-character-purple"
                style={{
                  height: (isTyping || (password.length > 0 && !showPassword)) ? '440px' : '400px',
                  transform: (password.length > 0 && showPassword)
                    ? 'skewX(0deg)'
                    : (isTyping || (password.length > 0 && !showPassword))
                      ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(40px)`
                      : `skewX(${purplePos.bodySkew || 0}deg)`,
                }}
              >
                <div
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? '20px' : isLookingAtEachOther ? '55px' : `${45 + purplePos.faceX}px`,
                    top: (password.length > 0 && showPassword) ? '35px' : isLookingAtEachOther ? '65px' : `${40 + purplePos.faceY}px`,
                  }}
                >
                  <EyeBall size={18} pupilSize={7} maxDistance={5} eyeColor="white" pupilColor="#2D2D2D" isBlinking={isPurpleBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 4 : undefined}
                  />
                  <EyeBall size={18} pupilSize={7} maxDistance={5} eyeColor="white" pupilColor="#2D2D2D" isBlinking={isPurpleBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 4 : undefined}
                  />
                </div>
              </div>

              {/* 黑色角色 */}
              <div
                ref={blackRef}
                className="login-character-black"
                style={{
                  transform: (password.length > 0 && showPassword)
                    ? 'skewX(0deg)'
                    : isLookingAtEachOther
                      ? `skewX(${(blackPos.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)`
                      : (isTyping || (password.length > 0 && !showPassword))
                        ? `skewX(${(blackPos.bodySkew || 0) * 1.5}deg)`
                        : `skewX(${blackPos.bodySkew || 0}deg)`,
                }}
              >
                <div
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? '10px' : isLookingAtEachOther ? '32px' : `${26 + blackPos.faceX}px`,
                    top: (password.length > 0 && showPassword) ? '28px' : isLookingAtEachOther ? '12px' : `${32 + blackPos.faceY}px`,
                  }}
                >
                  <EyeBall size={16} pupilSize={6} maxDistance={4} eyeColor="white" pupilColor="#2D2D2D" isBlinking={isBlackBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                  <EyeBall size={16} pupilSize={6} maxDistance={4} eyeColor="white" pupilColor="#2D2D2D" isBlinking={isBlackBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                </div>
              </div>

              {/* 橙色角色 */}
              <div
                ref={orangeRef}
                className="login-character-orange"
                style={{ transform: (password.length > 0 && showPassword) ? 'skewX(0deg)' : `skewX(${orangePos.bodySkew || 0}deg)` }}
              >
                <div
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? '50px' : `${82 + (orangePos.faceX || 0)}px`,
                    top: (password.length > 0 && showPassword) ? '85px' : `${90 + (orangePos.faceY || 0)}px`,
                  }}
                >
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D"
                    forceLookX={(password.length > 0 && showPassword) ? -5 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : undefined}
                  />
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D"
                    forceLookX={(password.length > 0 && showPassword) ? -5 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : undefined}
                  />
                </div>
              </div>

              {/* 黄色角色 */}
              <div
                ref={yellowRef}
                className="login-character-yellow"
                style={{ transform: (password.length > 0 && showPassword) ? 'skewX(0deg)' : `skewX(${yellowPos.bodySkew || 0}deg)` }}
              >
                <div
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? '20px' : `${52 + (yellowPos.faceX || 0)}px`,
                    top: (password.length > 0 && showPassword) ? '35px' : `${40 + (yellowPos.faceY || 0)}px`,
                  }}
                >
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D"
                    forceLookX={(password.length > 0 && showPassword) ? -5 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : undefined}
                  />
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D"
                    forceLookX={(password.length > 0 && showPassword) ? -5 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : undefined}
                  />
                </div>
                <div
                  className="login-character-mouth"
                  style={{
                    left: (password.length > 0 && showPassword) ? '10px' : `${40 + (yellowPos.faceX || 0)}px`,
                    top: (password.length > 0 && showPassword) ? '88px' : `${88 + (yellowPos.faceY || 0)}px`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="login-bottom-links">
            <a href="#" className="login-bottom-link">隐私政策</a>
            <a href="#" className="login-bottom-link">服务条款</a>
            <a href="#" className="login-bottom-link">联系我们</a>
          </div>
        </div>

        {/* 右侧注册表单区 */}
        <div className="login-right-section">
          <div className="login-form-wrapper">
            <div className="login-mobile-logo">
              <div className="login-brand-icon">
                <Sparkles className="login-brand-icon-svg" />
              </div>
              <span className="login-brand-name">PlanHub</span>
            </div>

            <div className="login-header">
              <h1 className="login-title">创建账户</h1>
              <p className="login-subtitle">开始您的计划管理之旅</p>
            </div>

            <form onSubmit={handleSubmit} className="login-form">
              <div className="login-form-field">
                <label htmlFor="username" className="login-form-label">用户名</label>
                <input
                  id="username"
                  type="text"
                  placeholder="请输入用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onFocus={() => setIsTyping(true)}
                  onBlur={() => setIsTyping(false)}
                  required
                  minLength={3}
                  maxLength={50}
                  className="login-form-input"
                />
              </div>

              <div className="login-form-field">
                <label htmlFor="displayName" className="login-form-label">显示名称</label>
                <input
                  id="displayName"
                  type="text"
                  placeholder="请输入显示名称"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  onFocus={() => setIsTyping(true)}
                  onBlur={() => setIsTyping(false)}
                  required
                  maxLength={100}
                  className="login-form-input"
                />
              </div>

              <div className="login-form-field">
                <label htmlFor="email" className="login-form-label">邮箱</label>
                <input
                  id="email"
                  type="email"
                  placeholder="请输入邮箱"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setIsTyping(true)}
                  onBlur={() => setIsTyping(false)}
                  required
                  className="login-form-input"
                />
              </div>

              <div className="login-form-field">
                <label htmlFor="password" className="login-form-label">密码</label>
                <div className="login-password-wrapper">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    required
                    className="login-form-input login-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="login-password-toggle"
                  >
                    {showPassword ? <EyeOff className="login-toggle-icon" /> : <Eye className="login-toggle-icon" />}
                  </button>
                </div>
              </div>

              <div className="login-form-field">
                <label htmlFor="confirmPassword" className="login-form-label">确认密码</label>
                <div className="login-password-wrapper">
                  <input
                    id="confirmPassword"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    required
                    className="login-form-input login-password-input"
                  />
                </div>
              </div>

              {error && (
                <div className="login-error-message">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="login-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? '注册中...' : '注册'}
              </button>
            </form>

            <div className="login-signup-wrapper">
              <span>已有账户? </span>
              <Link to="/login" className="login-signup-link">
                立即登录
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
