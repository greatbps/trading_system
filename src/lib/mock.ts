import type {
  Candidate, CandidateDetail, DecisionEvent, DebugLog,
  MarketRegime, SystemHealth, Position, Trade,
  StrategyPerf, RiskMetric, PeriodPerf, OHLCV,
  NewsItem, SupplyFlow, SimilarPattern, FilterStat,
} from '@/src/types/trading'

// ─── Market ──────────────────────────────────────────────────────────────────

export const MOCK_REGIME: MarketRegime = {
  regime: 'TREND', score: 78, vix: 18.4, adx: 32.1,
  trend: 82, momentum: 71, volume: 65, risk: 38,
}

export const MOCK_HEALTH: SystemHealth = {
  dataFeed:    { status: 'ok',   latency: 3  },
  orderRouter: { status: 'ok',   latency: 12 },
  riskEngine:  { status: 'ok',   latency: 1  },
  signalGen:   { status: 'warn', latency: 45 },
}

// ─── Filter Stats ─────────────────────────────────────────────────────────────

export const MOCK_FILTER_STATS: FilterStat[] = [
  { stage: 1, total: 120, passed: 28 },
  { stage: 2, total: 28,  passed: 5  },
]

// ─── Candidates ───────────────────────────────────────────────────────────────

export const MOCK_CANDIDATES: Candidate[] = [
  {
    symbol: '000660', name: 'SK하이닉스', price: 178500, changePct: 1.24,
    sparkline: [40, 45, 42, 48, 52, 50, 55, 58, 54, 60],
    entryScore: 87, riskScore: 23, confidence: 0.92,
    chochGrade: 'A', volRatio: 3.2, rsi: 58,
    conditions: [
      { key: 'choch', label: 'CHoCH', pass: true,  value: 'A' },
      { key: 'htf',   label: 'HTF',   pass: true,  value: 'TREND' },
      { key: 'vol',   label: 'VOL',   pass: true,  value: '3.2x' },
      { key: 'rsi',   label: 'RSI',   pass: true,  value: '58' },
    ],
    nearMiss: false, strategy: 'SMC',
    newsScore: 8.2, supplyScore: 7.8, technicalScore: 9.1,
    filterStage: 2, aiExpectation: 2.1,
  },
  {
    symbol: '005930', name: '삼성전자', price: 68400, changePct: -0.52,
    sparkline: [60, 55, 58, 52, 48, 50, 45, 48, 52, 55],
    entryScore: 62, riskScore: 45, confidence: 0.71,
    chochGrade: 'B', volRatio: 1.1, rsi: 72,
    conditions: [
      { key: 'choch', label: 'CHoCH', pass: true,  value: 'B' },
      { key: 'htf',   label: 'HTF',   pass: false, value: 'SIDEWAYS' },
      { key: 'vol',   label: 'VOL',   pass: true,  value: '1.1x' },
      { key: 'rsi',   label: 'RSI',   pass: false, value: '72 (>70)' },
    ],
    nearMiss: true, strategy: 'SMC',
    newsScore: 5.1, supplyScore: 6.3, technicalScore: 5.8,
    filterStage: 1, aiExpectation: 0.8,
  },
  {
    symbol: '035420', name: 'NAVER', price: 196500, changePct: 2.31,
    sparkline: [30, 35, 40, 38, 45, 50, 55, 52, 58, 65],
    entryScore: 78, riskScore: 38, confidence: 0.84,
    chochGrade: 'A', volRatio: 2.8, rsi: 61,
    conditions: [
      { key: 'choch', label: 'CHoCH', pass: true,  value: 'A' },
      { key: 'htf',   label: 'HTF',   pass: true,  value: 'TREND' },
      { key: 'vol',   label: 'VOL',   pass: false, value: '0.8x (<2)' },
      { key: 'rsi',   label: 'RSI',   pass: true,  value: '61' },
    ],
    nearMiss: false, strategy: 'SMC',
    newsScore: 7.4, supplyScore: 5.9, technicalScore: 7.8,
    filterStage: 2, aiExpectation: 1.5,
  },
  {
    symbol: '051910', name: 'LG화학', price: 296000, changePct: 0.67,
    sparkline: [50, 52, 51, 53, 54, 55, 54, 56, 57, 58],
    entryScore: 91, riskScore: 18, confidence: 0.96,
    chochGrade: 'A', volRatio: 4.1, rsi: 55,
    conditions: [
      { key: 'choch', label: 'CHoCH', pass: true, value: 'A' },
      { key: 'htf',   label: 'HTF',   pass: true, value: 'TREND' },
      { key: 'vol',   label: 'VOL',   pass: true, value: '4.1x' },
      { key: 'rsi',   label: 'RSI',   pass: true, value: '55' },
    ],
    nearMiss: false, strategy: 'SMC',
    newsScore: 9.0, supplyScore: 8.5, technicalScore: 9.3,
    filterStage: 2, aiExpectation: 2.8,
  },
  {
    symbol: '068270', name: '셀트리온', price: 171000, changePct: -0.21,
    sparkline: [45, 48, 46, 50, 48, 52, 55, 53, 56, 58],
    entryScore: 54, riskScore: 42, confidence: 0.58,
    chochGrade: 'B', volRatio: 1.8, rsi: 48,
    conditions: [
      { key: 'choch', label: 'CHoCH', pass: false, value: 'B (11:30 cut)' },
      { key: 'htf',   label: 'HTF',   pass: true,  value: 'TREND' },
      { key: 'vol',   label: 'VOL',   pass: true,  value: '1.8x' },
      { key: 'rsi',   label: 'RSI',   pass: true,  value: '48' },
    ],
    nearMiss: true, strategy: 'SMC',
    newsScore: 6.1, supplyScore: 4.8, technicalScore: 6.5,
    filterStage: 1, aiExpectation: 1.0,
  },
]

// ─── Research Card data per symbol ────────────────────────────────────────────

const RESEARCH_DATA: Record<string, {
  newsSummary: string
  newsItems: NewsItem[]
  supplySummary: string
  supplyFlow: SupplyFlow
  technicalSummary: string
  aiExpectation: number
  similarPatterns: SimilarPattern[]
  filterPassReason: string
}> = {
  '000660': {
    newsSummary: 'HBM3E 수주 확대 기대감 + 엔비디아 공급망 지위 강화로 긍정적 모멘텀 지속',
    newsItems: [
      { text: 'SK하이닉스, 엔비디아 HBM3E 단독 공급 가능성', sentiment: 'positive', impact: 0.85, source: '한국경제', time: '09:12' },
      { text: 'AI 반도체 수요 증가로 HBM 가격 상승 전망', sentiment: 'positive', impact: 0.72, source: '매일경제', time: '08:34' },
      { text: '2분기 실적 컨센서스 상향 조정', sentiment: 'positive', impact: 0.61, source: '이데일리', time: '07:55' },
    ],
    supplySummary: '외국인·기관 동반 순매수 3일 연속 지속. 프로그램 매수세도 가세',
    supplyFlow: { foreign: 128, institution: 85, program: 42, retailNet: -255, days: 3 },
    technicalSummary: 'CHoCH A등급 + EMA9>EMA21>EMA60 정배열. VWAP 상단 안착. RSI 58 (과매수 아님)',
    aiExpectation: 2.1,
    similarPatterns: [
      { date: '2025-06-12', holdDays: 2, returnPct: 3.2, regime: 'TREND' },
      { date: '2025-07-01', holdDays: 1, returnPct: 1.8, regime: 'TREND' },
      { date: '2025-07-15', holdDays: 3, returnPct: -0.5, regime: 'VOLATILE' },
    ],
    filterPassReason: 'HTF 추세 확인 + 유동성 스윕 + 리클레임 → 3/3 통과. 거래량 3.2x, CHoCH-A',
  },
  '005930': {
    newsSummary: '파운드리 사업부 수주 회복 기대. 단기 RSI 과열 구간으로 조심 필요',
    newsItems: [
      { text: '삼성전자 파운드리, 퀄컴 2nm 수주 협상 진행', sentiment: 'positive', impact: 0.55, source: '조선비즈', time: '09:01' },
      { text: 'DX부문 스마트폰 판매 부진 우려', sentiment: 'negative', impact: -0.42, source: '서울경제', time: '08:20' },
    ],
    supplySummary: '기관 소폭 매수, 외국인 관망. 수급 모멘텀 약함',
    supplyFlow: { foreign: -12, institution: 34, program: 8, retailNet: -30, days: 1 },
    technicalSummary: 'HTF SIDEWAYS 구간. RSI 72 과매수 영역 진입. CHoCH B등급으로 신뢰도 낮음',
    aiExpectation: 0.8,
    similarPatterns: [
      { date: '2025-05-20', holdDays: 1, returnPct: 0.9, regime: 'SIDEWAYS' },
      { date: '2025-06-08', holdDays: 2, returnPct: -1.2, regime: 'SIDEWAYS' },
    ],
    filterPassReason: '1차 필터 통과. HTF SIDEWAYS + RSI 과열로 2차 필터 미통과 (보류)',
  },
  '035420': {
    newsSummary: 'AI 검색 광고 수익 개선 + 클라우드 성장세. 네이버플러스 구독 확대',
    newsItems: [
      { text: '네이버 AI 검색, 광고 단가 18% 상승 효과', sentiment: 'positive', impact: 0.78, source: '디지털타임스', time: '09:22' },
      { text: '하이퍼클로바X 기업 고객 확대 발표', sentiment: 'positive', impact: 0.65, source: '연합뉴스', time: '08:45' },
      { text: '일본 라인야후 지분 리스크 잔존', sentiment: 'negative', impact: -0.31, source: '한국경제', time: '07:30' },
    ],
    supplySummary: '외국인 3일 연속 순매수. 기관 소폭 관망. 수급은 긍정적이나 거래량 미흡',
    supplyFlow: { foreign: 76, institution: 18, program: 22, retailNet: -116, days: 3 },
    technicalSummary: 'CHoCH A등급이나 거래량 부족 (0.8x). VWAP 상단 안착. 거래량 확인 후 진입 권장',
    aiExpectation: 1.5,
    similarPatterns: [
      { date: '2025-06-25', holdDays: 2, returnPct: 2.1, regime: 'TREND' },
      { date: '2025-07-10', holdDays: 1, returnPct: 1.4, regime: 'TREND' },
      { date: '2025-08-01', holdDays: 3, returnPct: -0.8, regime: 'VOLATILE' },
    ],
    filterPassReason: 'HTF 추세 + CHoCH-A 통과. 거래량 기준 미달 (0.8x < 2x) 조건 부적합 표시',
  },
  '051910': {
    newsSummary: '배터리 소재 수주 급증 + 전기차 전환 수혜주. 기관 집중 매수 포착',
    newsItems: [
      { text: 'LG화학, GM·볼보 배터리 소재 장기 계약 체결', sentiment: 'positive', impact: 0.92, source: '전자신문', time: '09:05' },
      { text: '양극재 생산능력 2배 확장 투자 발표', sentiment: 'positive', impact: 0.81, source: '매일경제', time: '08:30' },
      { text: '2025 하반기 실적 대폭 상향 전망', sentiment: 'positive', impact: 0.75, source: 'KBS경제', time: '07:50' },
    ],
    supplySummary: '외국인·기관 동시 대규모 순매수. 5일 연속 매수 지속. 강력한 수급 모멘텀',
    supplyFlow: { foreign: 215, institution: 142, program: 68, retailNet: -425, days: 5 },
    technicalSummary: 'CHoCH A등급 + 거래량 4.1x. EMA 정배열 + RSI 55 적정 구간. VWAP 상단 강세',
    aiExpectation: 2.8,
    similarPatterns: [
      { date: '2025-05-15', holdDays: 3, returnPct: 4.1, regime: 'TREND' },
      { date: '2025-06-18', holdDays: 2, returnPct: 2.9, regime: 'TREND' },
      { date: '2025-07-22', holdDays: 1, returnPct: 1.8, regime: 'TREND' },
    ],
    filterPassReason: '전 조건 통과 (4/4). CHoCH-A + HTF TREND + VOL 4.1x + RSI 55. 최고 신뢰도',
  },
  '068270': {
    newsSummary: '짐펜트라 미국 판매 확대 기대. 단기 B등급 CHoCH으로 진입 보류 중',
    newsItems: [
      { text: '셀트리온 짐펜트라, FDA 추가 적응증 승인 기대', sentiment: 'positive', impact: 0.68, source: '바이오타임즈', time: '09:18' },
      { text: '유럽 바이오시밀러 경쟁 심화 우려', sentiment: 'negative', impact: -0.45, source: '약업신문', time: '08:15' },
    ],
    supplySummary: '기관 관망, 외국인 소폭 매도. 수급 모멘텀 약함. 1차 필터에서 대기 중',
    supplyFlow: { foreign: -28, institution: 12, program: -8, retailNet: 24, days: 0 },
    technicalSummary: '11:30 이후 B등급 CHoCH로 시간 컷 적용. RSI 48 저점권이나 추세 미약',
    aiExpectation: 1.0,
    similarPatterns: [
      { date: '2025-06-30', holdDays: 2, returnPct: 1.5, regime: 'SIDEWAYS' },
      { date: '2025-07-14', holdDays: 1, returnPct: -0.9, regime: 'VOLATILE' },
    ],
    filterPassReason: '1차 통과. B등급 CHoCH 11:30 시간 제한 + 수급 약세로 2차 보류',
  },
}

// ─── OHLCV data ───────────────────────────────────────────────────────────────

function genOHLCV(basePrice: number, count = 40): OHLCV[] {
  const result: OHLCV[] = []
  let price = basePrice
  for (let i = 0; i < count; i++) {
    const move  = (Math.random() - 0.47) * basePrice * 0.007
    const open  = price
    const close = price + move
    const high  = Math.max(open, close) * (1 + Math.random() * 0.004)
    const low   = Math.min(open, close) * (1 - Math.random() * 0.004)
    const h = 9 + Math.floor(i / 12)
    const m = (i * 5) % 60
    result.push({
      time:   `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`,
      open:   Math.round(open),
      high:   Math.round(high),
      low:    Math.round(low),
      close:  Math.round(close),
      volume: Math.round(5000 + Math.random() * 20000),
    })
    price = close
  }
  return result
}

const OHLCV_CACHE: Record<string, OHLCV[]> = {}

export function getMockOHLCV(symbol: string, basePrice: number): OHLCV[] {
  if (!OHLCV_CACHE[symbol]) OHLCV_CACHE[symbol] = genOHLCV(basePrice)
  return OHLCV_CACHE[symbol]
}

// ─── Candidate Detail ─────────────────────────────────────────────────────────

export function getMockDetail(symbol: string): CandidateDetail {
  const candidate = MOCK_CANDIDATES.find(c => c.symbol === symbol)!
  const ohlcv     = getMockOHLCV(symbol, candidate?.price ?? 50000)
  const entryIdx  = 28
  const entryPrice = ohlcv[entryIdx].close
  const sl  = Math.round(entryPrice * 0.979)
  const tp  = Math.round(entryPrice * 1.026)
  const res = RESEARCH_DATA[symbol] ?? RESEARCH_DATA['000660']

  return {
    symbol,
    ohlcv,
    entryIndex: entryIdx,
    scores: [
      { name: 'NEWS',   score: Math.round(res.newsItems.reduce((a,n) => a + (n.sentiment === 'positive' ? n.impact * 10 : n.impact * 10 + 10), 0) / res.newsItems.length * 10), weight: 25, details: res.newsSummary.slice(0, 30) },
      { name: 'SUPPLY', score: Math.round((candidate?.supplyScore ?? 7) * 10), weight: 30, details: `외국인 ${res.supplyFlow.foreign > 0 ? '+' : ''}${res.supplyFlow.foreign}억 기관 ${res.supplyFlow.institution > 0 ? '+' : ''}${res.supplyFlow.institution}억` },
      { name: 'TECH',   score: Math.round((candidate?.technicalScore ?? 8) * 10), weight: 30, details: `CHoCH-${candidate?.chochGrade} VOL:${candidate?.volRatio}x RSI:${candidate?.rsi}` },
      { name: 'VOLUME', score: Math.min(100, Math.round((candidate?.volRatio ?? 2) * 22)), weight: 15, details: `${candidate?.volRatio}x avg 20MA` },
    ],
    totalScore:    candidate?.entryScore ?? 80,
    entryReason:   res.filterPassReason,
    sl, tp,
    rrRatio: +((tp - entryPrice) / (entryPrice - sl)).toFixed(1),
    positionSize: 10,
    // Research card
    newsSummary:    res.newsSummary,
    newsItems:      res.newsItems,
    supplySummary:  res.supplySummary,
    supplyFlow:     res.supplyFlow,
    technicalSummary: res.technicalSummary,
    aiExpectation:  res.aiExpectation,
    similarPatterns: res.similarPatterns,
    filterPassReason: res.filterPassReason,
  }
}

// ─── Decision Events ──────────────────────────────────────────────────────────

export const BASE_DECISION_LOG: DecisionEvent[] = [
  { id: 'd1',  time: '09:00:02.001', type: 'SYSTEM', symbol: '——', event: 'STARTUP',    params: 'mode:smc  grade_min:B  cutoff:12:30  size:10%  cons_loss:0', result: 'OK',     resultClass: 'info',   fnRef: 'main_auto_trading.py:1' },
  { id: 'd2',  time: '09:15:00.000', type: 'SYSTEM', symbol: '——', event: 'MKT_OPEN',   params: 'session:KRX  regime:TREND  adx:32.1  vix:18.4',               result: 'LIVE',   resultClass: 'info',   fnRef: 'market_context.py:45' },
  { id: 'd3',  time: '09:31:14.342', type: 'SCAN',   symbol: '005930', event: 'EMA_CROSS', params: 'ema9:68,400  ema21:67,800  vol:2.1x  rsi:68  gap:+0.8%',    result: 'PASS',   resultClass: 'pass',   fnRef: 'smc_signals.py:88' },
  { id: 'd4',  time: '09:32:01.108', type: 'FILTER', symbol: '005930', event: 'HTF_FAIL',  params: 'htf_regime:SIDEWAYS  expect:TREND  choch:B',               result: 'REJECT', resultClass: 'reject', fnRef: 'smc_signals.py:142', detail: 'HTF 5분봉 추세가 SIDEWAYS — A등급 CHoCH 있어도 진입 거부. HTF 필터는 EF 비율을 23%→11%로 낮춘 핵심 필터.' },
  { id: 'd5',  time: '10:14:38.221', type: 'SCAN',   symbol: '000660', event: 'CHOCH_A',   params: 'grade:A  vol:3.2x  rsi:58  gap:+1.2%  atr:1.42%',         result: 'PASS',   resultClass: 'pass',   fnRef: 'smc_structure.py:201' },
  { id: 'd6',  time: '10:16:05.440', type: 'FILTER', symbol: '000660', event: 'PREFILTER', params: 'htf_trend:OK(3)  sweep:OK(2)  reclaim:OK(1)  → 3/3',       result: 'PASS',   resultClass: 'pass',   fnRef: 'smc_signals.py:178' },
  { id: 'd7',  time: '10:16:05.441', type: 'FILTER', symbol: '000660', event: 'TIME_GATE', params: 'now:10:16  smc_cut:12:30  b_grade_cut:11:30  → OK',        result: 'PASS',   resultClass: 'pass',   fnRef: 'main_auto_trading.py:4367' },
  { id: 'd8',  time: '10:16:05.442', type: 'FILTER', symbol: '000660', event: 'COOLDOWN',  params: 'elapsed:∞  required:0m  cat:none  abs_block:false',        result: 'PASS',   resultClass: 'pass',   fnRef: 'reentry_metrics.py:89' },
  { id: 'd9',  time: '10:18:22.108', type: 'SCORE',  symbol: '000660', event: 'CALC',      params: 'news:8.2  supply:7.8  tech:9.1  vol:3.2x  → total:87',    result: '[87]',   resultClass: 'score',  fnRef: 'smc_signals.py:220' },
  { id: 'd10', time: '10:22:09.334', type: 'EXEC',   symbol: '000660', event: 'BUY',       params: 'price:175,500  qty:28  sl:171,000  size:10%  cons_loss:0',   result: 'OK',     resultClass: 'exec',   fnRef: 'main_auto_trading.py:4751' },
  { id: 'd11', time: '10:22:09.335', type: 'SYSTEM', symbol: '000660', event: 'SL_SET',    params: 'sl:171,000  method:swing_low-ATR×1.5  cap:-3%',             result: 'SET',    resultClass: 'adj',    fnRef: 'exit_logic_optimized.py:45' },
  { id: 'd12', time: '10:22:09.336', type: 'SYSTEM', symbol: '000660', event: 'EF_RESET',  params: 'atr_at_entry:2,490  mfe:0  follow_through:0  signals:[]',    result: 'WATCH',  resultClass: 'info',   fnRef: 'exit_logic_optimized.py:88' },
  { id: 'd13', time: '11:45:33.221', type: 'TRAIL',  symbol: '000660', event: 'SL_ADJ',    params: 'sl:171,000→173,000  mfe:177,200(+0.9%)  trigger:ATR_EXPAND', result: 'ADJ',    resultClass: 'adj',    fnRef: 'exit_logic_optimized.py:134' },
  { id: 'd14', time: '12:10:17.449', type: 'EXEC',   symbol: '000660', event: 'SELL',      params: 'price:178,800  pnl:+924K  pct:+1.9%  hold:108m  reason:trail', result: '+1.9%', resultClass: 'exec',  fnRef: 'main_auto_trading.py:4899' },
  { id: 'd15', time: '13:22:44.008', type: 'BLOCK',  symbol: '089490', event: 'MKT_CTX',   params: 'regime:VOLATILE  reason:ATR_COMPRESS(<0.8x avg)',           result: 'BLOCK',  resultClass: 'block',  fnRef: 'market_context.py:102', detail: 'ATR 14봉 평균 대비 0.74x — 변동성 압축으로 돌파 방향 예측 불가. market_context BLOCK.' },
  { id: 'd16', time: '13:55:02.114', type: 'BLOCK',  symbol: '005490', event: 'COOLDOWN',  params: 'cat:ef_no_demand  remain:22m  abs_block:true',             result: 'BLOCK',  resultClass: 'block',  fnRef: 'reentry_metrics.py:156', detail: 'EF no_demand 분류 — 수급 자체가 없었던 가짜 신호. 절대 재진입 불가 (abs_block=True).' },
  { id: 'd17', time: '14:01:00.000', type: 'SYSTEM', symbol: '——', event: 'TIME_CUT',    params: 'smc_cutoff:12:30  now:14:01  elapsed:91m  → 거래 종료',       result: 'CUT',    resultClass: 'info',   fnRef: 'main_auto_trading.py:4367' },
]

const SYMBOLS = MOCK_CANDIDATES.map(c => c.symbol)

export function generateDecisionEvent(): DecisionEvent {
  const types: DecisionEvent['type'][] = ['SCAN', 'FILTER', 'SCORE', 'BLOCK']
  const type  = types[Math.floor(Math.random() * types.length)]
  const sym   = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]
  const now   = new Date()
  const id    = `live_${Date.now()}_${Math.random()}`
  const ts    = `${now.toLocaleTimeString('ko-KR', { hour12: false })}.${String(now.getMilliseconds()).padStart(3,'0')}`
  const grade = Math.random() > 0.5 ? 'A' : 'B'
  const vol   = (1.5 + Math.random() * 2).toFixed(1)

  if (type === 'SCAN')   return { id, time: ts, type, symbol: sym, event: 'CHOCH_DETECT', params: `grade:${grade}  vol:${vol}x  rsi:${Math.round(45 + Math.random() * 30)}`, result: 'PASS', resultClass: 'pass', fnRef: 'smc_structure.py:201' }
  if (type === 'FILTER') return { id, time: ts, type, symbol: sym, event: 'HTF_CHECK', params: `htf:${Math.random() > 0.4 ? 'TREND' : 'SIDEWAYS'}  choch:${grade}  news_score:${(5 + Math.random() * 4).toFixed(1)}`, result: Math.random() > 0.4 ? 'PASS' : 'REJECT', resultClass: Math.random() > 0.4 ? 'pass' : 'reject', fnRef: 'smc_signals.py:142' }
  if (type === 'SCORE')  return { id, time: ts, type, symbol: sym, event: 'CALC', params: `news:${(5+Math.random()*4).toFixed(1)}  supply:${(4+Math.random()*5).toFixed(1)}  tech:${(5+Math.random()*4).toFixed(1)}`, result: `[${Math.round(65+Math.random()*25)}]`, resultClass: 'score', fnRef: 'smc_signals.py:220' }
  return { id, time: ts, type: 'BLOCK', symbol: sym, event: 'COOLDOWN', params: `remain:${Math.round(5+Math.random()*30)}m  cat:ef_no_demand`, result: 'BLOCK', resultClass: 'block', fnRef: 'reentry_metrics.py:89' }
}

// ─── Debug Logs ───────────────────────────────────────────────────────────────

export const BASE_DEBUG_LOG: DebugLog[] = [
  { id: 'dbg1',  level: 'INFO',  time: '10:22:09.330', module: 'main_auto_trading.py:4749',    msg: 'check_entry_signal(000660) → score=87 threshold=70' },
  { id: 'dbg2',  level: 'DEBUG', time: '10:22:09.331', module: 'smc_signals.py:178',            msg: 'prefilter 3/3 conditions passed' },
  { id: 'dbg3',  level: 'DEBUG', time: '10:22:09.332', module: 'reentry_metrics.py:89',         msg: 'cooldown check: no previous trade for 000660' },
  { id: 'dbg4',  level: 'DEBUG', time: '10:22:09.333', module: 'risk_manager.py:45',            msg: 'position_size=10% account=500M qty=28' },
  { id: 'dbg5',  level: 'INFO',  time: '10:22:09.334', module: 'main_auto_trading.py:4751',    msg: 'execute_buy(000660, 175500, qty=28)' },
]

export function generateDebugLog(): DebugLog {
  const sym = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]
  const now = new Date()
  const levels: DebugLog['level'][] = ['DEBUG', 'DEBUG', 'DEBUG', 'INFO', 'INFO', 'WARN']
  const level = levels[Math.floor(Math.random() * levels.length)]
  const msgs = [
    { m: 'smc_signals.py:88',          msg: `check_choch(${sym}) grade=${Math.random() > 0.5 ? 'A' : 'B'} vol=${(1.5+Math.random()*2).toFixed(1)}x` },
    { m: 'reentry_metrics.py:89',       msg: `cooldown_check(${sym}) elapsed=${Math.round(Math.random()*120)}m required=${Math.round(Math.random()*60)}m` },
    { m: 'risk_manager.py:45',          msg: `position_size_check() open_pos=${Math.round(Math.random()*3)} max=3` },
    { m: 'market_context.py:45',        msg: `regime_check() adx=${(25+Math.random()*20).toFixed(1)} trend=${Math.random() > 0.5 ? 'UP' : 'SIDEWAYS'}` },
    { m: 'exit_logic_optimized.py:134', msg: `ef_check(${sym}) signals=[${Math.random() > 0.7 ? 'direction_fail(2)' : ''}] threshold=3` },
  ]
  const { m, msg } = msgs[Math.floor(Math.random() * msgs.length)]
  return { id: `live_${Date.now()}_${Math.random()}`, level, time: now.toLocaleTimeString('ko-KR', { hour12: false }) + '.' + String(now.getMilliseconds()).padStart(3,'0'), module: m, msg }
}

// ─── Positions ────────────────────────────────────────────────────────────────

export const MOCK_POSITIONS: Position[] = [
  {
    symbol: '051910', name: 'LG화학', entryPrice: 290000, currentPrice: 296000,
    quantity: 17, sl: 283700, tp: 307500, pnl: 102000, pnlPct: 2.07,
    strategy: 'SMC', holdMinutes: 78, chochGrade: 'A',
  },
]

// ─── Trades ───────────────────────────────────────────────────────────────────

export const MOCK_TRADES: Trade[] = [
  { id: 't1', symbol: '000660', name: 'SK하이닉스', strategy: 'SMC', entryPrice: 175500, exitPrice: 178800, quantity: 28, pnl: 924000, pnlPct: 1.88,  win: true,  duration: '1h48m', exitReason: 'trail_stop_triggered', exitTag: 'TRAIL_STOP', time: '12:10', newsScoreAtEntry: 8.2, supplyScoreAtEntry: 7.8, technicalScoreAtEntry: 9.1 },
  { id: 't2', symbol: '035420', name: 'NAVER',    strategy: 'SMC', entryPrice: 192000, exitPrice: 189200, quantity: 26, pnl: -728000, pnlPct: -1.46, win: false, duration: '22m',   exitReason: 'Early Failure[no_demand]', exitTag: 'EF', time: '11:22', newsScoreAtEntry: 7.4, supplyScoreAtEntry: 4.2, technicalScoreAtEntry: 6.8 },
  { id: 't3', symbol: '051910', name: 'LG화학',  strategy: 'SMC', entryPrice: 284000, exitPrice: 290000, quantity: 17, pnl: 1020000, pnlPct: 2.11,  win: true,  duration: '2h10m', exitReason: 'trail_stop', exitTag: 'TRAIL_STOP', time: '10:05', newsScoreAtEntry: 9.0, supplyScoreAtEntry: 8.5, technicalScoreAtEntry: 9.3 },
  { id: 't4', symbol: '005930', name: '삼성전자', strategy: 'SMC', entryPrice: 69200, exitPrice: 68200, quantity: 72, pnl: -720000, pnlPct: -1.45, win: false, duration: '45m',   exitReason: 'hard_stop',  exitTag: 'HARD_STOP',  time: '09:51', newsScoreAtEntry: 5.1, supplyScoreAtEntry: 3.8, technicalScoreAtEntry: 5.2 },
]

// ─── Performance ─────────────────────────────────────────────────────────────

// 오늘 실현 PnL: 924K - 728K + 1,020K - 720K = 496K + 현재 포지션 평가익 102K
export const MOCK_TODAY: PeriodPerf = { pnl: 598000, pct: 0.12, trades: 4, winRate: 50 }
export const MOCK_WEEK:  PeriodPerf = { pnl: 8750000, pct: 1.75 }
export const MOCK_MONTH: PeriodPerf = { pnl: 24300000, pct: 4.86 }

export const MOCK_STRATEGY_PERF: StrategyPerf[] = [
  { code: 'SMC-A', name: 'SMC Grade A',  winRate: 72, avgReturn: 2.14, trades: 67, sharpe: 2.14, maxDD: -2.8 },
  { code: 'SMC-B', name: 'SMC Grade B',  winRate: 54, avgReturn: 0.92, trades: 89, sharpe: 0.94, maxDD: -4.2 },
  { code: 'EF-NF', name: 'EF no_follow', winRate: 68, avgReturn: 1.82, trades: 42, sharpe: 1.82, maxDD: -1.9 },
  { code: 'TRAIL', name: 'Trail Stop',   winRate: 61, avgReturn: 0.85, trades: 234, sharpe: 1.21, maxDD: -3.1 },
]

export const MOCK_RISK_METRICS: RiskMetric[] = [
  { label: 'MAX_DD',  value: '-4.2%',  status: 'ok',   description: 'Max drawdown in period' },
  { label: 'VAR_95',  value: '2,480K', status: 'ok',   description: '95% Value at Risk (daily)' },
  { label: 'SHARPE',  value: '1.67',   status: 'ok',   description: 'Sharpe ratio (annualized)' },
  { label: 'WIN_STK', value: '4',      status: 'ok',   description: 'Current win streak' },
  { label: 'LSE_STK', value: '0',      status: 'ok',   description: 'Current loss streak' },
  { label: 'CORR_KS', value: '0.42',   status: 'warn', description: 'Correlation to KOSPI' },
]

export { MOCK_FILTER_STATS }
export type { FilterStat }
