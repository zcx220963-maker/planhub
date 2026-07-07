import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { userApi } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowLeft, Eye, EyeOff, Lock, Sparkles } from 'lucide-react';
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

const ChangePassword: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
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
    const anyPassword = oldPassword + newPassword + confirmPassword;
    const anyVisible = showOldPassword || showNewPassword || showConfirmPassword;
    
    if (anyPassword.length > 0 && anyVisible) {
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
  }, [oldPassword, newPassword, confirmPassword, showOldPassword, showNewPassword, showConfirmPassword]);

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
    setSuccess(false);

    if (!user) {
      setError('请先登录');
      return;
    }

    if (newPassword.length < 8) {
      setError('新密码长度至少为8个字符');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (oldPassword === newPassword) {
      setError('新密码不能与原密码相同');
      return;
    }

    setIsLoading(true);

    try {
      await userApi.changePassword(user.id, { oldPassword, newPassword });
      setSuccess(true);
      setTimeout(() => {
        navigate('/profile');
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.message || '密码修改失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const anyPassword = oldPassword + newPassword + confirmPassword;
  const anyVisible = showOldPassword || showNewPassword || showConfirmPassword;

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
            <h2 className="login-intro-title">保护您的账户</h2>
            <h2 className="login-intro-title">安全第一</h2>
            <p className="login-intro-text">定期更改密码，保护您的个人信息安全。</p>
          </div>

          <div className="login-characters-container">
            <div className="login-characters-wrapper">
              <div 
                ref={purpleRef}
                className="login-character-purple"
                style={{
                  height: (isTyping || (anyPassword.length > 0 && !anyVisible)) ? '440px' : '400px',
                  transform: (anyPassword.length > 0 && anyVisible)
                    ? `skewX(0deg)`
                    : (isTyping || (anyPassword.length > 0 && !anyVisible))
                      ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(40px)` 
                      : `skewX(${purplePos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (anyPassword.length > 0 && anyVisible) ? `${20}px` : isLookingAtEachOther ? `${55}px` : `${45 + purplePos.faceX}px`,
                    top: (anyPassword.length > 0 && anyVisible) ? `${35}px` : isLookingAtEachOther ? `${65}px` : `${40 + purplePos.faceY}px`,
                  }}
                >
                  <EyeBall 
                    size={18} 
                    pupilSize={7} 
                    maxDistance={5} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isPurpleBlinking}
                    forceLookX={(anyPassword.length > 0 && anyVisible) ? (isPurplePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={(anyPassword.length > 0 && anyVisible) ? (isPurplePeeking ? 5 : -4) : isLookingAtEachOther ? 4 : undefined}
                  />
                  <EyeBall 
                    size={18} 
                    pupilSize={7} 
                    maxDistance={5} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isPurpleBlinking}
                    forceLookX={(anyPassword.length > 0 && anyVisible) ? (isPurplePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={(anyPassword.length > 0 && anyVisible) ? (isPurplePeeking ? 5 : -4) : isLookingAtEachOther ? 4 : undefined}
                  />
                </div>
              </div>

              <div 
                ref={blackRef}
                className="login-character-black"
                style={{
                  transform: (anyPassword.length > 0 && anyVisible)
                    ? `skewX(0deg)`
                    : isLookingAtEachOther
                      ? `skewX(${(blackPos.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)`
                      : (isTyping || (anyPassword.length > 0 && !anyVisible))
                        ? `skewX(${(blackPos.bodySkew || 0) * 1.5}deg)` 
                        : `skewX(${blackPos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (anyPassword.length > 0 && anyVisible) ? `${10}px` : isLookingAtEachOther ? `${32}px` : `${26 + blackPos.faceX}px`,
                    top: (anyPassword.length > 0 && anyVisible) ? `${28}px` : isLookingAtEachOther ? `${12}px` : `${32 + blackPos.faceY}px`,
                  }}
                >
                  <EyeBall 
                    size={16} 
                    pupilSize={6} 
                    maxDistance={4} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isBlackBlinking}
                    forceLookX={(anyPassword.length > 0 && anyVisible) ? -4 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(anyPassword.length > 0 && anyVisible) ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                  <EyeBall 
                    size={16} 
                    pupilSize={6} 
                    maxDistance={4} 
                    eyeColor="white" 
                    pupilColor="#2D2D2D" 
                    isBlinking={isBlackBlinking}
                    forceLookX={(anyPassword.length > 0 && anyVisible) ? -4 : isLookingAtEachOther ? 0 : undefined}
                    forceLookY={(anyPassword.length > 0 && anyVisible) ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                </div>
              </div>

              <div 
                ref={orangeRef}
                className="login-character-orange"
                style={{
                  transform: (anyPassword.length > 0 && anyVisible) ? `skewX(0deg)` : `skewX(${orangePos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (anyPassword.length > 0 && anyVisible) ? `${50}px` : `${82 + (orangePos.faceX || 0)}px`,
                    top: (anyPassword.length > 0 && anyVisible) ? `${85}px` : `${90 + (orangePos.faceY || 0)}px`,
                  }}
                >
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(anyPassword.length > 0 && anyVisible) ? -5 : undefined} forceLookY={(anyPassword.length > 0 && anyVisible) ? -4 : undefined} />
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(anyPassword.length > 0 && anyVisible) ? -5 : undefined} forceLookY={(anyPassword.length > 0 && anyVisible) ? -4 : undefined} />
                </div>
              </div>

              <div 
                ref={yellowRef}
                className="login-character-yellow"
                style={{
                  transform: (anyPassword.length > 0 && anyVisible) ? `skewX(0deg)` : `skewX(${yellowPos.bodySkew || 0}deg)`,
                }}
              >
                <div 
                  className="login-character-eyes"
                  style={{
                    left: (anyPassword.length > 0 && anyVisible) ? `${20}px` : `${52 + (yellowPos.faceX || 0)}px`,
                    top: (anyPassword.length > 0 && anyVisible) ? `${35}px` : `${40 + (yellowPos.faceY || 0)}px`,
                  }}
                >
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(anyPassword.length > 0 && anyVisible) ? -5 : undefined} forceLookY={(anyPassword.length > 0 && anyVisible) ? -4 : undefined} />
                  <Pupil size={12} maxDistance={5} pupilColor="#2D2D2D" forceLookX={(anyPassword.length > 0 && anyVisible) ? -5 : undefined} forceLookY={(anyPassword.length > 0 && anyVisible) ? -4 : undefined} />
                </div>
                <div 
                  className="login-character-mouth"
                  style={{
                    left: (anyPassword.length > 0 && anyVisible) ? `${10}px` : `${40 + (yellowPos.faceX || 0)}px`,
                    top: (anyPassword.length > 0 && anyVisible) ? `${88}px` : `${88 + (yellowPos.faceY || 0)}px`,
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
              <button 
                onClick={() => navigate(-1)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#64748b',
                  padding: '8px',
                  borderRadius: '8px',
                  transition: 'background-color 0.2s',
                  marginRight: 'auto',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <ArrowLeft size={20} />
                <span>返回</span>
              </button>
              <h1 className="login-title">修改密码</h1>
              <p className="login-subtitle">请输入您的密码信息</p>
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px', color: '#64748b' }}>
              <Shield size={48} />
            </div>

            {success && (
              <div className="login-error-message" style={{ backgroundColor: '#dcfce7', color: '#166534', borderColor: '#bbf7d0' }}>
                密码修改成功！即将跳转到个人资料页面...
              </div>
            )}

            {error && (
              <div className="login-error-message">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="login-form">
              <div className="login-form-field">
                <label className="login-form-label">原密码</label>
                <div className="login-password-wrapper">
                  <input
                    type={showOldPassword ? 'text' : 'password'}
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    placeholder="请输入原密码"
                    className="login-form-input login-password-input"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowOldPassword(!showOldPassword)}
                    className="login-password-toggle"
                  >
                    {showOldPassword ? (
                      <EyeOff className="login-toggle-icon" />
                    ) : (
                      <Eye className="login-toggle-icon" />
                    )}
                  </button>
                </div>
              </div>

              <div className="login-form-field">
                <label className="login-form-label">新密码</label>
                <div className="login-password-wrapper">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    placeholder="请输入新密码（至少8个字符）"
                    className="login-form-input login-password-input"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="login-password-toggle"
                  >
                    {showNewPassword ? (
                      <EyeOff className="login-toggle-icon" />
                    ) : (
                      <Eye className="login-toggle-icon" />
                    )}
                  </button>
                </div>
              </div>

              <div className="login-form-field">
                <label className="login-form-label">确认新密码</label>
                <div className="login-password-wrapper">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    placeholder="请再次输入新密码"
                    className="login-form-input login-password-input"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="login-password-toggle"
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="login-toggle-icon" />
                    ) : (
                      <Eye className="login-toggle-icon" />
                    )}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="login-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? '修改中...' : '修改密码'}
              </button>
            </form>

            <div className="login-signup-wrapper">
              <span>返回个人资料? </span>
              <button
                type="button"
                onClick={() => navigate('/profile')}
                className="login-signup-link"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, font: 'inherit' }}
              >
                点击返回
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChangePassword;