import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Sparkles } from 'lucide-react';
import './Login.css';

interface PupilProps {
  size?: number;
  maxDistance?: number;
  pupilColor?: string;
  forceLookX?: number;
  forceLookY?: number;
}

const Pupil = ({ 
  size = 12, 
  maxDistance = 5,
  pupilColor = "#2D2D2D",
  forceLookX,
  forceLookY
}: PupilProps) => {
  const [mouseX, setMouseX] = useState<number>(0);
  const [mouseY, setMouseY] = useState<number>(0);
  const pupilRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  const calculatePupilPosition = () => {
    if (!pupilRef.current) return { x: 0, y: 0 };

    if (forceLookX !== undefined && forceLookY !== undefined) {
      return { x: forceLookX, y: forceLookY };
    }

    const pupil = pupilRef.current.getBoundingClientRect();
    const pupilCenterX = pupil.left + pupil.width / 2;
    const pupilCenterY = pupil.top + pupil.height / 2;

    const deltaX = mouseX - pupilCenterX;
    const deltaY = mouseY - pupilCenterY;
    const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);

    const angle = Math.atan2(deltaY, deltaX);
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;

    return { x, y };
  };

  const pupilPos = calculatePupilPosition();

  return (
    <div
      ref={pupilRef}
      className="login-pupil"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: pupilColor,
        transform: `translate(${pupilPos.x}px, ${pupilPos.y}px)`,
      }}
    />
  );
};

interface EyeBallProps {
  size?: number;
  pupilSize?: number;
  maxDistance?: number;
  eyeColor?: string;
  pupilColor?: string;
  isBlinking?: boolean;
  forceLookX?: number;
  forceLookY?: number;
}

const EyeBall = ({ 
  size = 48, 
  pupilSize = 16, 
  maxDistance = 10,
  eyeColor = "white",
  pupilColor = "#2D2D2D",
  isBlinking = false,
  forceLookX,
  forceLookY
}: EyeBallProps) => {
  const [mouseX, setMouseX] = useState<number>(0);
  const [mouseY, setMouseY] = useState<number>(0);
  const eyeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  const calculatePupilPosition = () => {
    if (!eyeRef.current) return { x: 0, y: 0 };

    if (forceLookX !== undefined && forceLookY !== undefined) {
      return { x: forceLookX, y: forceLookY };
    }

    const eye = eyeRef.current.getBoundingClientRect();
    const eyeCenterX = eye.left + eye.width / 2;
    const eyeCenterY = eye.top + eye.height / 2;

    const deltaX = mouseX - eyeCenterX;
    const deltaY = mouseY - eyeCenterY;
    const distance = Math.min(Math.sqrt(deltaX ** 2 + deltaY ** 2), maxDistance);

    const angle = Math.atan2(deltaY, deltaX);
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;

    return { x, y };
  };

  const pupilPos = calculatePupilPosition();

  return (
    <div
      ref={eyeRef}
      className="login-eyeball"
      style={{
        width: `${size}px`,
        height: isBlinking ? '2px' : `${size}px`,
        backgroundColor: eyeColor,
      }}
    >
      {!isBlinking && (
        <div
          className="login-eyeball-pupil"
          style={{
            width: `${pupilSize}px`,
            height: `${pupilSize}px`,
            backgroundColor: pupilColor,
            transform: `translate(${pupilPos.x}px, ${pupilPos.y}px)`,
          }}
        />
      )}
    </div>
  );
};

const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mouseX, setMouseX] = useState<number>(0);
  const [mouseY, setMouseY] = useState<number>(0);
  const [isPurpleBlinking, setIsPurpleBlinking] = useState(false);
  const [isBlackBlinking, setIsBlackBlinking] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false);
  const [isPurplePeeking, setIsPurplePeeking] = useState(false);
  const purpleRef = useRef<HTMLDivElement>(null);
  const blackRef = useRef<HTMLDivElement>(null);
  const yellowRef = useRef<HTMLDivElement>(null);
  const orangeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    const getRandomBlinkInterval = () => Math.random() * 4000 + 3000;
    const scheduleBlink = () => {
      const blinkTimeout = setTimeout(() => {
        setIsPurpleBlinking(true);
        setTimeout(() => {
          setIsPurpleBlinking(false);
          scheduleBlink();
        }, 150);
      }, getRandomBlinkInterval());
      return blinkTimeout;
    };
    const timeout = scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    const getRandomBlinkInterval = () => Math.random() * 4000 + 3000;
    const scheduleBlink = () => {
      const blinkTimeout = setTimeout(() => {
        setIsBlackBlinking(true);
        setTimeout(() => {
          setIsBlackBlinking(false);
          scheduleBlink();
        }, 150);
      }, getRandomBlinkInterval());
      return blinkTimeout;
    };
    const timeout = scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (isTyping) {
      setIsLookingAtEachOther(true);
      const timer = setTimeout(() => {
        setIsLookingAtEachOther(false);
      }, 800);
      return () => clearTimeout(timer);
    } else {
      setIsLookingAtEachOther(false);
    }
  }, [isTyping]);

  useEffect(() => {
    if (password.length > 0 && showPassword) {
      const schedulePeek = () => {
        const peekInterval = setTimeout(() => {
          setIsPurplePeeking(true);
          setTimeout(() => {
            setIsPurplePeeking(false);
          }, 800);
        }, Math.random() * 3000 + 2000);
        return peekInterval;
      };
      const firstPeek = schedulePeek();
      return () => clearTimeout(firstPeek);
    } else {
      setIsPurplePeeking(false);
    }
  }, [password, showPassword]);

  const calculatePosition = (ref: React.RefObject<HTMLDivElement | null>) => {
    if (!ref.current) return { faceX: 0, faceY: 0, bodySkew: 0 };

    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 3;

    const deltaX = mouseX - centerX;
    const deltaY = mouseY - centerY;

    const faceX = Math.max(-15, Math.min(15, deltaX / 20));
    const faceY = Math.max(-10, Math.min(10, deltaY / 30));
    const bodySkew = Math.max(-6, Math.min(6, -deltaX / 120));

    return { faceX, faceY, bodySkew };
  };

  const purplePos = calculatePosition(purpleRef);
  const blackPos = calculatePosition(blackRef);
  const yellowPos = calculatePosition(yellowRef);
  const orangePos = calculatePosition(orangeRef);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login({ username, password });
      navigate('/dashboard');
    } catch {
      setError('用户名或密码错误');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-grid">
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
            <h2 className="login-intro-title">让每一次打卡</h2>
            <h2 className="login-intro-title">都充满意义</h2>
            <p className="login-intro-text">Track your goals, achieve your dreams, and build habits that last.</p>
          </div>

          <div className="login-characters-container">
            <div className="login-characters-wrapper">
              <div 
                ref={purpleRef}
                className="login-character-purple"
                style={{
                  height: (isTyping || (password.length > 0 && !showPassword)) ? '440px' : '400px',
                  transform: (password.length > 0 && showPassword)
                    ? `skewX(0deg)`
                    : (isTyping || (password.length > 0 && !showPassword))
                      ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(40px)` 
                      : `skewX(${purplePos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? `${20}px` : isLookingAtEachOther ? `${55}px` : `${45 + purplePos.faceX}px`,
                    top: (password.length > 0 && showPassword) ? `${35}px` : isLookingAtEachOther ? `${65}px` : `${40 + purplePos.faceY}px`,
                  }}
                >
                  <EyeBall 
                    size={18} 
                    pupilSize={7} 
                    maxDistance={5} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isPurpleBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? (isPurplePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? (isPurplePeeking ? 5 : -4) : isLookingAtEachOther ? 4 : undefined}
                  />
                  <EyeBall 
                    size={18} 
                    pupilSize={7} 
                    maxDistance={5} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isPurpleBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? (isPurplePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? (isPurplePeeking ? 5 : -4) : isLookingAtEachOther ? 4 : undefined}
                  />
                </div>
              </div>

              <div 
                ref={blackRef}
                className="login-character-black"
                style={{
                  transform: (password.length > 0 && showPassword)
                    ? `skewX(0deg)`
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
                    left: (password.length > 0 && showPassword) ? `${10}px` : isLookingAtEachOther ? `${32}px` : `${26 + blackPos.faceX}px`,
                    top: (password.length > 0 && showPassword) ? `${28}px` : isLookingAtEachOther ? `${12}px` : `${32 + blackPos.faceY}px`,
                  }}
                >
                  <EyeBall 
                    size={16} 
                    pupilSize={6} 
                    maxDistance={4} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isBlackBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                  <EyeBall 
                    size={16} 
                    pupilSize={6} 
                    maxDistance={4} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isBlackBlinking}
                    forceLookX={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(password.length > 0 && showPassword) ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                </div>
              </div>

              <div 
                ref={orangeRef}
                className="login-character-orange"
                style={{
                  transform: (password.length > 0 && showPassword) ? `skewX(0deg)` : `skewX(${orangePos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? `${50}px` : `${82 + (orangePos.faceX || 0)}px`,
                    top: (password.length > 0 && showPassword) ? `${85}px` : `${90 + (orangePos.faceY || 0)}px`,
                  }}
                >
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(password.length > 0 && showPassword) ? -5 : undefined} forceLookY={(password.length > 0 && showPassword) ? -4 : undefined} />
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(password.length > 0 && showPassword) ? -5 : undefined} forceLookY={(password.length > 0 && showPassword) ? -4 : undefined} />
                </div>
              </div>

              <div 
                ref={yellowRef}
                className="login-character-yellow"
                style={{
                  transform: (password.length > 0 && showPassword) ? `skewX(0deg)` : `skewX(${yellowPos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (password.length > 0 && showPassword) ? `${20}px` : `${52 + (yellowPos.faceX || 0)}px`,
                    top: (password.length > 0 && showPassword) ? `${35}px` : `${40 + (yellowPos.faceY || 0)}px`,
                  }}
                >
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(password.length > 0 && showPassword) ? -5 : undefined} forceLookY={(password.length > 0 && showPassword) ? -4 : undefined} />
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(password.length > 0 && showPassword) ? -5 : undefined} forceLookY={(password.length > 0 && showPassword) ? -4 : undefined} />
                </div>
                <div 
                  className="login-character-mouth"
                  style={{
                    left: (password.length > 0 && showPassword) ? `${10}px` : `${40 + (yellowPos.faceX || 0)}px`,
                    top: (password.length > 0 && showPassword) ? `${88}px` : `${88 + (yellowPos.faceY || 0)}px`,
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

        <div className="login-right-section">
          <div className="login-form-wrapper">
            <div className="login-mobile-logo">
              <div className="login-brand-icon">
                <Sparkles className="login-brand-icon-svg" />
              </div>
              <span className="login-brand-name">PlanHub</span>
            </div>

            <div className="login-header">
              <h1 className="login-title">欢迎回来!</h1>
              <p className="login-subtitle">请输入您的账户信息</p>
            </div>

            <form onSubmit={handleSubmit} className="login-form">
              <div className="login-form-field">
                <label htmlFor="username" className="login-form-label">用户名</label>
                <input
                  id="username"
                  type="text"
                  placeholder="请输入用户名"
                  value={username}
                  autoComplete="off"
                  onChange={(e) => setUsername(e.target.value)}
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
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="login-form-input login-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="login-password-toggle"
                  >
                    {showPassword ? (
                      <EyeOff className="login-toggle-icon" />
                    ) : (
                      <Eye className="login-toggle-icon" />
                    )}
                  </button>
                </div>
              </div>

              <div className="login-form-options">
                <label className="login-remember-label">
                  <input type="checkbox" className="login-remember-checkbox" />
                  <span>记住我 30 天</span>
                </label>
                <button
                  type="button"
                  className="login-forgot-link"
                  onClick={() => setInfoMessage('忘记密码功能暂未开放，请联系管理员重置密码')}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, font: 'inherit' }}
                >
                  忘记密码?
                </button>
              </div>

              {error && (
                <div className="login-error-message">
                  {error}
                </div>
              )}

              {infoMessage && (
                <div className="login-info-message">
                  {infoMessage}
                </div>
              )}

              <button
                type="submit"
                className="login-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? "登录中..." : "登录"}
              </button>
            </form>

            <div className="login-signup-wrapper">
              <span>还没有账户? </span>
              <Link to="/register" className="login-signup-link">
                立即注册
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
