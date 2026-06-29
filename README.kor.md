# :moneybag: 개인 재무 웹사이트

## [웹사이트 가기](https://personal-finance-website.onrender.com/)

## 소개

이 사이트는 사용자의 대만 달러·미국 달러 현금 보유량과 대만 주식 보유 현황을 표시하도록 설계되었습니다. 대만 주식 정보는 해당 거래일의 대만 증권거래소 최신 종가를 반영합니다.

    참고:
    무료 요금제로 Render 를 사용하고 있어,15분 동안 요청이 없으면 서버가 자동으로 절전 상태가 됩니다. 그 결과 첫 화면 로딩이
    지연될 수 있습니다. 양해 부탁드립니다.

## 기술 스텍

- 백엔드:`Python3`
- 프론트엔드:`JavaScript`, `HTML`, `CSS`
- 프레임워크: `Bootstrap`, `Flask`
- 데이터베이스:`MySQL`(Used `SQLite3` for testing)
- 클라우드 서비스: `TiDB Cloud`, `Render`
- API:[Global Real-Time Exchange Rate API](https://tw.rter.info/howto_currencyapi.php)

## 테스트 계정

| 이메일 | 비밀번호 |
| --- | --- |
| wang569 | 12345 |
| cindy0925 | flyaway |
| amy54yun | 25896 |

> 새로운 계정을 직접 생성하여 이용하시거나, 위의 테스트 계정으로 로그인하여 기능을 확인하실 수 있습니다.

## 사용자 인터페이스

#### 로그인 화면:

![](static/images/login.png)

#### 회원가입 화면:

![](static/images/register.png)

#### 메인 대시보드:

![](static/images/homepage-1.png)
![](static/images/homepage-2.png)

#### 현금 거래 입력:

![](static/images/cash_form.png)

#### 주식 거래 입력:

![](static/images/stock_form.png)

#### 현금 거래 내역:

![](static/images/cash_transaction_records.png)

#### 주식 보유 현황:

![](static/images/stock_holdings.png)
