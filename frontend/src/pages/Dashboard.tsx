import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, Target, CheckCircle, TrendingUp, ArrowUpRight, ArrowDownRight, Calendar, Clock, Plus } from 'lucide-react';
import { planApi, checkinApi } from '../services/api';
import type { Plan } from '../types';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [checkinCounts, setCheckinCounts] = useState<{ [key: number]: number }>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    planApi.getAllPlans()
      .then(async (data) => {
        setPlans(data);
        const counts = await Promise.all(
          data.map(async (plan) => {
            try {
              const checkins = await checkinApi.getCheckinsByPlanId(plan.id);
              return { planId: plan.id, count: checkins.length };
            } catch (err) {
              return { planId: plan.id, count: 0 };
            }
          })
        );
        const countMap: { [key: number]: number } = {};
        counts.forEach(item => {
          countMap[item.planId] = item.count;
        });
        setCheckinCounts(countMap);
      })
      .catch(() => setPlans([]))
      .finally(() => setLoading(false));
  }, []);

  const stats = [
    {
      title: '总计划',
      value: plans.length,
      icon: LayoutDashboard,
      trend: '+12%',
      trendUp: true,
      color: '#333333',
      onClick: () => navigate('/my-plans'),
    },
    {
      title: '进行中',
      value: plans.filter(p => p.status === 'ACTIVE').length,
      icon: Target,
      trend: '+8%',
      trendUp: true,
      color: '#333333',
      onClick: () => navigate('/my-plans?status=active'),
    },
    {
      title: '已完成',
      value: plans.filter(p => p.status === 'COMPLETED').length,
      icon: CheckCircle,
      trend: '-2%',
      trendUp: false,
      color: '#333333',
      onClick: () => navigate('/my-plans?status=completed'),
    },
    {
      title: '待开始',
      value: plans.filter(p => p.status === 'PENDING').length,
      icon: Clock,
      trend: '+5%',
      trendUp: true,
      color: '#333333',
      onClick: () => navigate('/my-plans?status=pending'),
    },
  ];

  const recentPlans = plans.slice(0, 4);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '#f1f5f9';
      case 'ACTIVE': return '#f1f5f9';
      case 'PENDING': return '#f1f5f9';
      case 'PAUSED': return '#f1f5f9';
      case 'CANCELLED': return '#f1f5f9';
      case 'DRAFT': return '#f1f5f9';
      default: return '#f1f5f9';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '已完成';
      case 'ACTIVE': return '进行中';
      case 'PENDING': return '待开始';
      case 'PAUSED': return '已暂停';
      case 'CANCELLED': return '已取消';
      case 'DRAFT': return '草稿';
      default: return status;
    }
  };

  return (
    <div className="dashboard">
      <div style={{ padding: '32px 40px 0', maxWidth: '1600px', margin: '0 auto' }}>
        <div style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '16px', marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#0f172a', margin: '0 0 8px' }}>首页</h1>
              <p style={{ fontSize: '16px', color: '#64748b', margin: 0 }}>欢迎回来，查看您的计划概览</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px', backgroundColor: '#f1f5f9', borderRadius: '10px', fontSize: '14px', fontWeight: 500, color: '#333333' }}>
              <Calendar size={16} />
              <span>{new Date().toLocaleDateString('zh-CN')}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-container">
        <div className="dashboard-stats-grid">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              className="dashboard-stat-card"
              onClick={stat.onClick}
            >
              <div className="dashboard-stat-icon" style={{ background: '#f1f5f9', border: '1px solid #e2e8f0' }}>
                <Icon size={24} style={{ color: '#333333' }} />
              </div>
              <div className="dashboard-stat-content">
                <p className="dashboard-stat-title">{stat.title}</p>
                <p className="dashboard-stat-value">{stat.value}</p>
                <div className={`dashboard-stat-trend ${stat.trendUp ? 'up' : 'down'}`}>
                  {stat.trendUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                  <span>{stat.trend}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px', marginTop: '32px' }}>
        <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid #e2e8f0' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', margin: 0 }}>最近计划</h2>
            <button
              onClick={() => navigate('/my-plans')}
              style={{ padding: '8px 16px', background: '#000000', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}
            >
              查看全部
            </button>
          </div>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>加载中...</div>
          ) : plans.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>暂无计划</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1, overflowY: 'auto' }}>
              {recentPlans.slice(0, 4).map((plan) => (
                <div
                  key={plan.id}
                  onClick={() => navigate(`/my-plans?planId=${plan.id}`)}
                  style={{ padding: '14px', background: '#f8fafc', borderRadius: '12px', cursor: 'pointer', transition: 'all 0.3s ease', border: '1px solid #e2e8f0' }}
                >
                  <div style={{ marginBottom: '10px' }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', margin: '0 0 4px 0' }}>{plan.title}</h3>
                    <p style={{ fontSize: '12px', color: '#64748b', margin: '0 0 8px 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{plan.description || '暂无描述'}</p>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span style={{ padding: '3px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: 600, color: '#000000', backgroundColor: getStatusColor(plan.status) }}>
                        {getStatusText(plan.status)}
                      </span>
                      <span style={{ padding: '3px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: 600, background: 'rgba(0, 0, 0, 0.06)', color: '#1f2937' }}>
                        已打卡 {checkinCounts[plan.id] || 0} 天
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ flex: 1, height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', background: '#000000', borderRadius: '3px', transition: 'width 0.6s ease', width: `${plan.progressPercentage}%` }}></div>
                    </div>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', width: '35px', textAlign: 'right' }}>{plan.progressPercentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid #e2e8f0' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', margin: 0 }}>计划进度</h2>
              <button
                onClick={() => navigate('/my-plans')}
                style={{ padding: '8px 16px', background: '#000000', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}
              >
                查看全部
              </button>
            </div>
            {plans.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>暂无计划数据</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
                {plans.slice(0, 4).map((plan) => (
                  <div
                    key={plan.id}
                    onClick={() => navigate(`/my-plans?planId=${plan.id}`)}
                    style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px', background: '#f8fafc', borderRadius: '10px', cursor: 'pointer', transition: 'all 0.3s ease' }}
                  >
                    <span style={{ fontSize: '12px', fontWeight: 500, color: '#0f172a', width: '70px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{plan.title.length > 10 ? plan.title.slice(0, 10) + '...' : plan.title}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ height: '20px', background: '#e2e8f0', borderRadius: '6px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: '#000000', borderRadius: '6px', transition: 'width 0.8s ease', width: `${plan.progressPercentage}%` }}></div>
                      </div>
                    </div>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', width: '45px', textAlign: 'right' }}>{plan.progressPercentage}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', flex: 1 }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', margin: '0 0 20px 0' }}>快速操作</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px', flex: 1 }}>
              <button onClick={() => navigate('/my-plans')} style={{ padding: '18px 12px', border: '1px solid #e2e8f0', borderRadius: '12px', background: '#f8fafc', color: '#333333', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', transition: 'all 0.3s ease' }}>
                <Plus size={24} />
                <span>创建计划</span>
              </button>
              <button onClick={() => navigate('/community')} style={{ padding: '18px 12px', border: '1px solid #e2e8f0', borderRadius: '12px', background: '#f8fafc', color: '#333333', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', transition: 'all 0.3s ease' }}>
                <TrendingUp size={24} />
                <span>社区动态</span>
              </button>
              <button onClick={() => navigate('/my-plans?status=completed')} style={{ padding: '18px 12px', border: '1px solid #e2e8f0', borderRadius: '12px', background: '#f8fafc', color: '#333333', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', transition: 'all 0.3s ease' }}>
                <CheckCircle size={24} />
                <span>已完成</span>
              </button>
              <button onClick={() => navigate('/profile')} style={{ padding: '18px 12px', border: '1px solid #e2e8f0', borderRadius: '12px', background: '#f8fafc', color: '#333333', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', transition: 'all 0.3s ease' }}>
                <Calendar size={24} />
                <span>个人中心</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default Dashboard;