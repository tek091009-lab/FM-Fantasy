(function(){
  'use strict';
  const css=`
    #fmMobileBar,#fmMobileBackdrop,#fmMobileNav{display:none}
    @media(max-width:900px){
      :root{--fm-mobile-bar:58px}
      html,body{width:100%;max-width:100%;overflow-x:hidden}
      body{min-width:0!important}
      .app{display:block!important;width:100%!important;min-width:0!important}
      #fmMobileBar{position:fixed;inset:0 0 auto 0;height:var(--fm-mobile-bar);z-index:10020;display:flex;align-items:center;gap:11px;padding:8px 12px;box-sizing:border-box;background:linear-gradient(110deg,#170728 0%,#4f0b68 55%,#a50a79 100%);border-bottom:1px solid rgba(255,255,255,.14);box-shadow:0 8px 24px rgba(0,0,0,.28)}
      #fmMobileMenu{width:40px;height:40px;border:1px solid rgba(255,255,255,.2);border-radius:10px;background:#25123f;color:#fff;font-size:22px;line-height:1;display:grid;place-items:center;flex:0 0 auto}
      #fmMobileBrand{font-weight:900;font-size:17px;white-space:nowrap}.fmMobileBrandAccent{color:#ff3b9d}
      #fmMobileTitle{margin-left:auto;max-width:45vw;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:800;color:#eaddf5;text-align:right}
      #fmMobileBackdrop{position:fixed;inset:0;z-index:10030;background:rgba(3,0,15,.68);backdrop-filter:blur(2px)}
      body.fmMobileOpen #fmMobileBackdrop{display:block}
      .sidebar{position:fixed!important;inset:0 auto 0 0!important;z-index:10040!important;display:flex!important;flex-direction:column!important;width:min(86vw,320px)!important;height:100dvh!important;min-height:0!important;padding:12px 10px!important;overflow-y:auto!important;overflow-x:hidden!important;transform:translateX(-105%);transition:transform .22s ease;background:linear-gradient(180deg,#150622,#090318 78%)!important;box-shadow:18px 0 40px rgba(0,0,0,.45)}
      body.fmMobileOpen .sidebar{transform:translateX(0)}
      body.fmMobileOpen{overflow:hidden}
      .sidebar .logo{display:flex!important;min-height:48px!important;margin:0 4px 5px!important;padding:2px 5px 8px!important}
      .sidebar .snav{display:flex!important;flex-direction:column!important;gap:2px!important;width:100%!important}
      .sidebar .snav button{display:flex!important;width:100%!important;min-height:42px!important;padding:0 12px!important;font-size:13px!important;text-align:left!important}
      .sidebar .snav button.subnav{min-height:34px!important;padding-left:31px!important;font-size:11px!important}
      .sidebar .syncbox{display:block!important;margin:10px 4px 8px!important;padding:10px!important;flex:0 0 auto!important}
      .sidebar .syncBtn{min-height:32px!important;font-size:9px!important}.sidebar .syncStatus,.sidebar .syncLeague{font-size:8px!important}
      .main{width:100%!important;max-width:100%!important;min-width:0!important;margin:0!important;padding:calc(var(--fm-mobile-bar) + 8px) 8px 14px!important;box-sizing:border-box!important;overflow:visible!important}
      .page{width:100%!important;max-width:100%!important;min-width:0!important;overflow:visible!important}
      .top{min-height:78px!important;height:auto!important;margin:0 0 8px!important;padding:13px 14px!important;border-radius:13px!important;align-items:flex-start!important}
      .top h1{font-size:24px!important;line-height:1.05!important}.top p{font-size:10px!important;margin-top:5px!important}
      .top .profile,.top .account,.top .managerPill{max-width:46%!important;transform:scale(.86);transform-origin:top right}
      .card,.summary,.tableCard{max-width:100%!important;box-sizing:border-box!important}
      .summary{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;height:auto!important;min-height:0!important;overflow:hidden!important}
      .summary .sum{min-width:0!important;min-height:72px!important;padding:10px 8px!important;text-align:center!important;border-bottom:1px solid rgba(189,126,235,.17)}
      .summary .sum:nth-child(odd){border-left:0!important}.summary .sum:nth-child(even){border-right:0!important}
      .summary small{font-size:9px!important}.summary b{font-size:16px!important;overflow-wrap:anywhere}
      .split,.teamGrid,.teamWorkspace,.starWorkspace,.fixtureWorkspace,.leagueBody,.statsBottom{display:grid!important;grid-template-columns:minmax(0,1fr)!important;grid-template-areas:none!important;gap:9px!important;width:100%!important;min-width:0!important}
      .teamGrid>* ,.starWorkspace>* ,.fixtureWorkspace>* ,.leagueBody>*{grid-area:auto!important;width:100%!important;min-width:0!important;max-width:100%!important;margin-left:0!important;margin-right:0!important}
      .pitchCard,.starPitchCard{height:auto!important;min-height:0!important;overflow:hidden!important;border-radius:11px!important}
      .pitchCard>.pitchScroll,.starPitchCard>.pitchScroll{display:block!important;position:relative!important;width:100%!important;max-width:100%!important;height:auto;min-height:0!important;overflow:hidden!important}
      .pitchCard>.pitchScroll>.pitch,.starPitchCard>.pitchScroll>.pitch,#txPitch{width:760px!important;min-width:760px!important;max-width:none!important;height:610px!important;min-height:610px!important;margin:0!important;transform:scale(var(--fm-mobile-pitch-scale,1));transform-origin:top left!important}
      .pitchTopControls,.gwNav,.gameweekNav{right:10px!important;left:auto!important;top:8px!important;transform:none!important;z-index:20!important}
      .bench{width:calc(100% - 20px)!important;left:10px!important;right:10px!important;min-width:720px!important}
      .teamHead,.starFooter{min-height:44px!important;height:auto!important;padding:7px 9px!important;margin:0!important}
      #teamSide,.teamSide,.starSide{min-height:260px!important;height:auto!important;margin:0!important}
      #viewBanner,#swapBanner{width:100%!important;margin:0 0 8px!important;box-sizing:border-box!important}
      #transfersPage .split{display:flex!important;flex-direction:column!important}
      #transfersPage .pitchCard{order:1}#transfersPage .market,#transfersPage .playerSelection,#transfersPage .right{order:2;width:100%!important;max-width:none!important}
      #transfersPage .summary{grid-template-columns:repeat(2,minmax(0,1fr))!important}
      #transfersPage .summary .sum:last-child:nth-child(odd){grid-column:1/-1!important}
      #transfersPage .prow{min-width:700px!important}.marketRows,.playerRows,.marketTable{overflow-x:auto!important;-webkit-overflow-scrolling:touch}
      .newsGrid{display:grid!important;grid-template-columns:1fr!important;gap:9px!important}.newsGrid>*{grid-column:auto!important;min-height:170px!important}.newsAbout{margin-top:9px!important}
      .fixtureSummary,.leagueStats,.statsHero{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
      .fixtureRail{display:grid!important;grid-template-columns:1fr!important;gap:9px!important}.fixtureMain{min-width:0!important}.fixtureFilters,.fixtureCalendar{width:100%!important}
      .fixtureRows,.fixtureList{overflow-x:auto!important;-webkit-overflow-scrolling:touch}.fixtureRow{min-width:680px!important}
      .fixtureSummary .fixtureSummaryCard{min-width:0!important;padding:10px!important}
      .tableTopbar{display:flex!important;align-items:flex-start!important;gap:8px!important;flex-wrap:wrap!important}.tableTabs{display:flex!important;width:100%!important;overflow-x:auto!important;white-space:nowrap!important}.leagueTableScroll{width:100%!important;max-height:66dvh!important;overflow:auto!important;-webkit-overflow-scrolling:touch}.leagueTable{min-width:900px!important}
      .leagueStats{grid-template-columns:repeat(2,minmax(0,1fr))!important}.leagueMine,.leagueRail{min-height:0!important}.leagueActions,.leagueCreateJoin{display:grid!important;grid-template-columns:1fr!important}.leagueFeatured{min-height:280px!important}
      .statsHero,.statsLeaderGrid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}.statsLeaderGrid>*{min-width:0!important}.statsBottom{grid-template-columns:1fr!important}.seasonInsightGrid{display:grid!important;grid-template-columns:1fr!important}.statsWorkspace{height:auto!important;min-height:0!important;overflow:visible!important}
      .rulesConceptGrid{display:grid!important;grid-template-columns:1fr!important;height:auto!important;min-height:0!important;overflow:visible!important}.ruleConceptCard{min-height:0!important;height:auto!important}.ruleConceptCard p,.ruleConceptCard li,.ruleMini{font-size:12px!important;line-height:1.45!important}.ruleMiniGrid,.ruleScoreGrid{grid-template-columns:1fr!important}
      .modal,.playerDrawer,.drawer,.compareModal{max-width:100vw!important}.playerDrawer,.drawer{width:100vw!important}.modalBox,.compareBox{width:calc(100vw - 16px)!important;max-width:none!important;max-height:calc(100dvh - 16px)!important;margin:8px!important;overflow:auto!important}.modalActions{display:grid!important;grid-template-columns:1fr!important}
      button,input,select{touch-action:manipulation}.btn,.pinkBtn,.primary{min-height:42px}
    }
    @media(max-width:560px){
      .main{padding-left:6px!important;padding-right:6px!important}.top{min-height:70px!important;padding:11px!important}.top h1{font-size:21px!important}.top p{max-width:58%;font-size:9px!important}
      .top .profile,.top .account,.top .managerPill{max-width:43%!important;transform:scale(.76)}
      .summary .sum{min-height:66px!important;padding:8px 5px!important}.summary b{font-size:14px!important}
      .fixtureSummary,.leagueStats,.statsHero,.statsLeaderGrid{grid-template-columns:1fr!important}
      .statsHero{grid-template-columns:repeat(2,minmax(0,1fr))!important}.statsHero>*{min-height:96px!important}
      .pitchCard>.pitchScroll>.pitch,.starPitchCard>.pitchScroll>.pitch,#txPitch{width:720px!important;min-width:720px!important;height:580px!important;min-height:580px!important}
      .bench{min-width:680px!important}
      .leagueTableScroll{max-height:70dvh!important}
    }
    @media(max-width:900px){
      /* Native phone pitch: the mobile view has its own geometry rather than a
         scaled or horizontally clipped desktop canvas. */
      .pitchCard>.pitchScroll,.starPitchCard>.pitchScroll{height:auto!important;min-height:0!important;overflow:visible!important}
      .pitchCard>.pitchScroll>.pitch,.starPitchCard>.pitchScroll>.pitch,#transfersPage .pitch{
        transform:none!important;width:100%!important;min-width:0!important;max-width:100%!important;
        height:auto!important;min-height:650px!important;margin:0!important;padding:14px 5px 10px!important;
        box-sizing:border-box!important;border-radius:16px!important;clip-path:none!important;
        background:repeating-linear-gradient(180deg,#08a94d 0,#08a94d 72px,#079b46 72px,#079b46 144px)!important
      }
      .pitchCard .halfPitchMarkings{inset:8px 7px 8px!important}.pitchCard .halfPitchMarkings .outline{clip-path:none!important;border-radius:12px!important}
      .pitchCard .pline{display:flex!important;width:100%!important;max-width:100%!important;justify-content:space-evenly!important;align-items:flex-start!important;gap:3px!important;box-sizing:border-box!important}
      .pitchCard .pline.gk{margin-top:15px!important}.pitchCard .pline.def{margin-top:72px!important}.pitchCard .pline.mid{margin-top:68px!important}.pitchCard .pline.fwd{margin-top:66px!important}
      .pitchCard .pchip{flex:0 1 72px!important;width:min(18vw,72px)!important;min-width:0!important;max-width:72px!important;min-height:91px!important;padding:5px 3px 6px!important;border-radius:9px!important;box-sizing:border-box!important;overflow:visible!important}
      .pitchCard .shirt{width:34px!important;height:36px!important;margin:0 auto 5px!important}.pitchCard .kitBadge{top:11px!important;transform:translateX(-50%) scale(.82)!important}
      .pitchCard .pchip b{display:-webkit-box!important;-webkit-line-clamp:2!important;-webkit-box-orient:vertical!important;min-height:20px!important;font-size:8.5px!important;line-height:1.12!important;overflow:hidden!important}
      .pitchCard .pchip span{display:block!important;font-size:7.5px!important;line-height:1.12!important;white-space:normal!important}
      .pitchCard .captag{top:3px!important;left:3px!important;width:17px!important;height:17px!important;font-size:7px!important}.pitchCard .statusFlag{top:3px!important;right:3px!important;min-width:20px!important;height:14px!important;font-size:6px!important}
      .pitchCard .centerCircle{width:150px!important;height:150px!important;bottom:-73px!important}
      .pitchCard .bench{position:relative!important;width:calc(100% - 12px)!important;min-width:0!important;max-width:none!important;margin:22px 6px 0!important;padding:10px 5px 11px!important;border-radius:13px!important;box-sizing:border-box!important}
      .pitchCard .benchGrid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:4px!important}.pitchCard .benchGrid>div{min-width:0!important}.pitchCard .bench .pchip{width:100%!important;max-width:78px!important;margin:0 auto!important}.pitchCard .slotLabel{font-size:7px!important;white-space:nowrap!important}
      #teamPage .pitchCard,#starPage .pitchCard{padding:0!important;border-radius:14px!important;background:#110927!important}
      #teamPage .pitchTopControls,#starPage .pitchTopControls{top:7px!important;right:7px!important}.gwNav{padding:3px!important}.gwArrow{width:27px!important;height:27px!important}.gwNav b{min-width:78px!important;font-size:8px!important}
      #teamPage .teamSide,#starPage .starSide{border-radius:14px!important}.chipButtons{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important}.chipButton{min-width:0!important}
      #transfersPage .pitchCard{padding:0!important}#transfersPage .pitchCard>.cardh{padding:14px 14px 11px!important}#transfersPage .pitchScroll{margin:0!important}
      #transfersPage .actionbar{display:grid!important;grid-template-columns:1fr!important;gap:9px!important;padding:11px!important}.transferDraftActions{display:grid!important;grid-template-columns:1fr!important;gap:7px!important}
    }
    @media(max-width:900px){
      /* Mobile is an application layout, not a reduced desktop canvas. */
      :root{--fm-mobile-nav:66px}
      body{background:radial-gradient(circle at 92% 4%,rgba(170,19,139,.16),transparent 28%),#080419!important}
      .main{padding-bottom:calc(var(--fm-mobile-nav) + 18px + env(safe-area-inset-bottom))!important}
      .page:not(.active){display:none!important}
      #fmMobileNav{position:fixed;z-index:10018;inset:auto 0 0 0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));min-height:var(--fm-mobile-nav);padding:6px 5px calc(5px + env(safe-area-inset-bottom));border-top:1px solid rgba(255,255,255,.13);background:rgba(13,5,31,.96);box-shadow:0 -10px 30px rgba(0,0,0,.36);backdrop-filter:blur(18px)}
      .fmMobileNavBtn{display:grid;place-items:center;align-content:center;gap:3px;min-width:0;border:0;border-radius:10px;color:#9f91b5;background:transparent;font:800 9px/1 Inter,system-ui,sans-serif}
      .fmMobileNavBtn i{display:grid;place-items:center;width:25px;height:22px;color:#c4b7d5;font-size:17px;font-style:normal}.fmMobileNavBtn.active{color:#fff;background:rgba(177,43,164,.18)}.fmMobileNavBtn.active i{color:#ff4ca5}
      .top{background:radial-gradient(circle at 100% 0,rgba(255,65,166,.32),transparent 34%),linear-gradient(120deg,#36125f,#8414b7 56%,#d2148c)!important}
      .top .profile,.top .account,.top .managerPill{margin-left:auto!important}

      /* Every pitch row owns the available phone width. No desktop coordinates survive. */
      .pitchCard .pline,.starPitchCard .pline,#transfersPage .pline{position:relative!important;inset:auto!important;transform:none!important;margin-left:0!important;margin-right:0!important}
      .pitchCard .pline.gk,.starPitchCard .pline.gk,#transfersPage .pline.gk{margin-top:19px!important}
      .pitchCard .pline.def,.starPitchCard .pline.def,#transfersPage .pline.def{margin-top:70px!important}
      .pitchCard .pline.mid,.starPitchCard .pline.mid,#transfersPage .pline.mid{margin-top:64px!important}
      .pitchCard .pline.fwd,.starPitchCard .pline.fwd,#transfersPage .pline.fwd{margin-top:62px!important}
      #transfersPage .pitch{display:flex!important;flex-direction:column!important;overflow:hidden!important}
      #transfersPage .pitch .pline{flex:0 0 auto!important}
      #transfersPage .pitchScroll{overflow:visible!important}

      /* News becomes a readable activity feed. */
      #newsPage{display:flex!important;flex-direction:column!important;gap:10px!important}
      #newsPage .newsStamp{margin:0!important;padding:11px 13px!important;border-radius:13px!important;font-size:9px!important;line-height:1.45!important;background:#17102f!important}
      #newsPage .newsGrid{display:flex!important;flex-direction:column!important;gap:10px!important}
      #newsPage .newsCard{min-height:0!important;height:auto!important;border-radius:16px!important;overflow:hidden!important}
      #newsPage .newsHead{min-height:60px!important;padding:10px 12px!important}#newsPage .newsHead h3{font-size:15px!important}#newsPage .newsHead .muted{font-size:8px!important}
      #newsPage .newsIcon{width:36px!important;height:36px!important;flex-basis:36px!important}
      #newsPage .newsRows{height:auto!important;max-height:none!important;padding:6px 9px 10px!important;overflow:visible!important}
      #newsPage .newsRow{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;gap:3px 9px!important;min-height:52px!important;padding:9px 7px!important;border-bottom:1px solid rgba(255,255,255,.07)!important;font-size:9px!important}
      #newsPage .newsRow>b{font-size:11px!important}#newsPage .newsRow>span{font-size:8px!important;text-align:right!important}#newsPage .newsRow>span:nth-of-type(n+2){grid-column:1/-1!important;text-align:left!important;color:#978aa9!important}
      #newsPage .newsTransferHead{display:none!important}#newsPage .newsSearch{height:40px!important;margin:4px 0 7px!important;font-size:11px!important}
      #newsPage .newsAbout{padding:13px!important;border-radius:15px!important}.newsAbout span{font-size:9px!important;line-height:1.45!important}

      /* Transfers: wallet, squad and player market are three native app sections. */
      #transfersPage{display:flex!important;flex-direction:column!important;gap:11px!important}
      #transfersPage>.summary{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;padding:0!important;border:0!important;background:transparent!important;overflow:visible!important}
      #transfersPage>.summary .sum{min-height:82px!important;border:1px solid rgba(197,154,231,.17)!important;border-radius:15px!important;background:linear-gradient(155deg,#211441,#160d31)!important;box-shadow:0 8px 22px rgba(0,0,0,.18)!important}
      #transfersPage>.summary .sum:last-child:nth-child(odd){grid-column:1/-1!important}
      #transfersPage .split{gap:11px!important}#transfersPage .pitchCard,#transfersPage .market{border-radius:16px!important;overflow:hidden!important}
      #transfersPage .pitchCard>.cardh{display:flex!important;align-items:center!important;gap:8px!important;padding:13px!important}#transfersPage .pitchCard>.cardh h2{font-size:18px!important}#transfersPage #autoFill{max-width:45%!important;padding:8px 10px!important;font-size:10px!important;white-space:normal!important}
      #transfersPage .rulebar{margin:8px!important;padding:9px!important;border-radius:10px!important;font-size:9px!important}
      #transfersPage .market>.cardh{min-height:64px!important;padding:12px 13px!important}#transfersPage .market>.cardh h2{font-size:19px!important}
      #transfersPage .toolbar{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important;padding:10px!important}
      #transfersPage .toolbar #search{grid-column:1/-1!important}#transfersPage .toolbar .ctrl,#transfersPage .toolbar .btn{width:100%!important;height:42px!important;min-width:0!important;font-size:10px!important}
      #transfersPage .tableWrap{max-height:68dvh!important;overflow-y:auto!important;overflow-x:hidden!important;-webkit-overflow-scrolling:touch}
      #transfersPage .thead{display:none!important}#transfersPage #marketRows{min-width:0!important;overflow:visible!important}
      #transfersPage .prow{display:grid!important;grid-template-columns:minmax(0,1fr) auto 38px!important;grid-template-areas:'player price action' 'club pos action'!important;gap:3px 8px!important;min-width:0!important;min-height:66px!important;padding:9px 10px!important;border-bottom:1px solid rgba(255,255,255,.07)!important}
      #transfersPage .prow>div:nth-child(1){grid-area:player!important}#transfersPage .prow>div:nth-child(2){grid-area:club!important;font-size:8px!important;color:#9588a6!important}#transfersPage .prow>div:nth-child(3){grid-area:pos!important}#transfersPage .prow>div:nth-child(4){grid-area:price!important;align-self:end!important;font-size:10px!important}#transfersPage .prow>div:nth-child(5){display:none!important}#transfersPage .prow>div:nth-child(6){grid-area:action!important;display:grid!important;place-items:center!important}
      #transfersPage .prow .pinfo{min-width:0!important}#transfersPage .prow .round{width:31px!important;height:31px!important;flex-basis:31px!important}.prow .add{width:34px!important;height:34px!important}
      #transfersPage .actionbar{border-top:1px solid rgba(255,255,255,.08)!important}.transferDraftActions{grid-template-columns:1fr 1fr!important}.transferDraftActions>*:first-child{grid-column:1/-1!important}

      /* Mini leagues use touch cards and a horizontal stat shelf. */
      #leaguesPage .leagueDashboard{display:flex!important;flex-direction:column!important;gap:11px!important}
      #leaguesPage .leagueStats{display:flex!important;gap:8px!important;overflow-x:auto!important;scroll-snap-type:x mandatory!important;padding:1px 1px 5px!important;background:transparent!important;border:0!important}
      #leaguesPage .leagueStat{flex:0 0 78%!important;min-height:88px!important;padding:12px!important;border:1px solid rgba(194,130,232,.17)!important;border-radius:15px!important;background:linear-gradient(150deg,#211440,#160c30)!important;scroll-snap-align:start!important}
      #leaguesPage .leagueStatIcon{width:38px!important;height:38px!important}.leagueStat b{font-size:20px!important}.leagueStat span{font-size:8px!important}
      #leaguesPage .leagueBody{display:flex!important;flex-direction:column!important;gap:10px!important}#leaguesPage .leagueMine{order:1!important;border-radius:16px!important;min-height:0!important}#leaguesPage .leagueRail{order:2!important;display:flex!important;flex-direction:column!important;gap:10px!important}
      #leaguesPage .leagueActionTabs{display:none!important}#leaguesPage .leagueActionGrid{display:flex!important;flex-direction:column!important;gap:0!important}#leaguesPage .leagueAction{grid-template-columns:42px minmax(0,1fr)!important;padding:15px!important}#leaguesPage .leagueAction+.leagueAction{border-left:0!important;border-top:1px solid rgba(255,255,255,.09)!important}
      #leaguesPage .leagueActionIcon{width:38px!important;height:38px!important}.leagueAction h3{font-size:14px!important}.leagueAction p{font-size:9px!important;line-height:1.45!important}.leagueAction .ctrl,.leagueAction .btn{width:100%!important;height:42px!important;margin-top:8px!important}
      #leaguesPage .leagueFeatured{min-height:0!important;border-radius:16px!important}#leaguesPage .fmFeaturedLeagueInner{padding:17px!important}.fmFeaturedName{font-size:21px!important}.fmFeaturedActions{display:grid!important;grid-template-columns:1fr 1fr!important;width:100%!important}.fmFeaturedAction{min-width:0!important;width:100%!important}
      #leaguesPage .leagueWhy{display:flex!important;gap:8px!important;overflow-x:auto!important;padding:0 0 5px!important;background:transparent!important;border:0!important}.leagueWhy .whyItem{flex:0 0 76%!important;min-height:74px!important;padding:12px!important;border:1px solid rgba(255,255,255,.1)!important;border-radius:14px!important;background:#17102f!important}

      /* Star XI keeps the squad presentation and condenses its overview underneath. */
      #starPage .starWorkspace{display:flex!important;flex-direction:column!important;gap:10px!important}
      #starPage .starSummary{display:flex!important;gap:7px!important;overflow-x:auto!important;padding:0 0 3px!important;border:0!important;background:transparent!important}
      #starPage .starSummary .sum{flex:0 0 42%!important;min-height:74px!important;border:1px solid rgba(194,130,232,.17)!important;border-radius:14px!important;background:#1c1138!important}
      #starPage .starPitchCard{order:2!important}#starPage .starSide{order:3!important;min-height:0!important;border-radius:16px!important;overflow:hidden!important}#starPage .starFooter{order:4!important;min-height:38px!important;border-radius:12px!important}
      #starPage .starSideHero{min-height:0!important;padding:16px!important}.starSideHero h3{font-size:21px!important}.starSideHero p{font-size:9px!important;line-height:1.45!important}.starOverview{padding:11px!important}.starMetric{min-height:43px!important}.starSideNote{margin:10px!important}

      /* League table: native tab rail plus a deliberate internal data scroller. */
      #tablePage .tableCard{border-radius:16px!important;overflow:hidden!important}.tableTopbar{padding:9px!important}.tableTabs{gap:5px!important;padding-bottom:2px!important}.tableTab{flex:0 0 auto!important;min-width:76px!important;height:38px!important;border-radius:10px!important;font-size:10px!important}.tableFixtures{width:100%!important}
      #tablePage .leagueTableScroll{max-height:72dvh!important;border-top:1px solid rgba(255,255,255,.08)!important}.leagueTable{min-width:760px!important;font-size:10px!important}.leagueTable th{height:39px!important;font-size:8px!important}.leagueTable td{height:48px!important;padding:5px 7px!important}
      .leagueTable th:first-child,.leagueTable td:first-child{position:sticky!important;left:0!important;z-index:5!important;width:38px!important;background:#171031!important}.leagueTable th:nth-child(2),.leagueTable td:nth-child(2){position:sticky!important;left:38px!important;z-index:4!important;min-width:190px!important;background:#171031!important;box-shadow:7px 0 10px rgba(0,0,0,.2)}

      /* Fixtures: the schedule is primary; filters open as an app sheet. */
      #fixturesPage .fixtureWorkspace{display:flex!important;flex-direction:column!important;gap:10px!important}
      #fixturesPage .fixtureSummary{display:flex!important;gap:7px!important;overflow-x:auto!important;padding:0 0 4px!important}.fixtureSummaryCard{flex:0 0 43%!important;min-height:76px!important;border-radius:14px!important;scroll-snap-align:start!important}.fixtureSummaryCard b{font-size:17px!important}
      #fixturesPage .fixtureMain{order:2!important;border-radius:16px!important;overflow:hidden!important}.fixtureListHead{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;gap:8px!important;padding:11px!important}.fixtureListHead h2{font-size:17px!important}.fixtureTopNav{grid-column:1/-1!important;justify-self:stretch!important;display:grid!important;grid-template-columns:34px minmax(0,1fr) 34px!important;width:100%!important}.fixtureTopNav b{justify-self:center!important}
      #fmFixtureFilterToggle{grid-column:2!important;grid-row:1!important;align-self:center!important;min-height:36px!important;border:1px solid rgba(255,255,255,.13);border-radius:10px;color:#fff;background:#281647;font:900 10px Inter,system-ui,sans-serif;padding:0 12px}
      #fixturesPage .fixtureRowsConcept{max-height:68dvh!important;overflow-y:auto!important;overflow-x:hidden!important;-webkit-overflow-scrolling:touch!important}
      #fixturesPage .fixtureConcept{margin:0 8px 8px!important;border:1px solid rgba(255,255,255,.08)!important;border-radius:12px!important;overflow:hidden!important;background:#17102f!important}
      #fixturesPage .fixtureHead{display:grid!important;grid-template-columns:minmax(0,1fr) 27px 63px 27px minmax(0,1fr) 15px!important;grid-template-areas:'gw gw time time time chevron' 'home homebadge result awaybadge away chevron'!important;gap:7px 4px!important;min-height:78px!important;padding:9px!important;align-items:center!important}
      .fixtureGWChip{grid-area:gw!important;justify-self:start!important}.fixtureKickoff{grid-area:time!important;justify-self:end!important}.fixtureTeam.home{grid-area:home!important;text-align:right!important}.fixtureTeam.away{grid-area:away!important;text-align:left!important}.fixtureBadge:nth-of-type(1){grid-area:homebadge!important}.fixtureResult{grid-area:result!important}.fixtureBadge:nth-of-type(2){grid-area:awaybadge!important}.fixtureChevron{grid-area:chevron!important}.fixtureTeam{font-size:9px!important;line-height:1.15!important}.fixtureResult{min-width:58px!important;font-size:11px!important}.fixtureResult small{font-size:6px!important}.fixtureDetail{padding:9px!important}
      #fixturesPage .fixtureRail{order:3!important;display:none!important;grid-template-rows:auto!important}.fmMobileFixtureFiltersOpen #fixturesPage .fixtureRail{display:flex!important;flex-direction:column!important;gap:9px!important}.fixtureFilters,.fixtureNavigator{border-radius:15px!important}.fixtureNavigator{display:none!important}.fixtureFilters{padding-bottom:11px!important}.fixtureFilters>label{font-size:9px!important}.fixtureFilters>.ctrl{height:40px!important;font-size:10px!important}.fixtureChecks{display:grid!important;grid-template-columns:1fr 1fr!important;gap:8px!important}.fixtureChecks label{min-height:31px!important;font-size:9px!important}

      /* Stats uses category tabs; only one full-size leaderboard is shown at a time. */
      #statsPage .statsWorkspace{display:flex!important;flex-direction:column!important;gap:9px!important;height:auto!important}
      #statsPage .statsToolbar{display:flex!important;align-items:center!important;gap:8px!important;min-height:58px!important;padding:10px!important;border-radius:14px!important}.statsToolbar>div{min-width:0!important}.statsToolbar b{font-size:12px!important}.statsToolbar span{font-size:8px!important}.statsToolbar .btn{margin-left:auto!important;padding:8px 10px!important;font-size:9px!important;white-space:nowrap!important}
      #statsPage .statsHero{display:flex!important;gap:8px!important;overflow-x:auto!important;padding:0 0 4px!important;scroll-snap-type:x mandatory!important}.statsHeroCard{flex:0 0 76%!important;min-height:94px!important;border-radius:15px!important;scroll-snap-align:start!important}.statsHeroCard span{font-size:12px!important}.statsHeroCard b{font-size:22px!important}
      .fmMobileStatTabs{display:flex!important;gap:6px!important;overflow-x:auto!important;padding:2px 0!important}.fmMobileStatTab{flex:0 0 auto;min-height:39px;padding:0 14px;border:1px solid rgba(255,255,255,.11);border-radius:999px;color:#b8aacb;background:#1b1136;font:900 10px Inter,system-ui,sans-serif}.fmMobileStatTab.active{color:#fff;border-color:#eb3c9c;background:linear-gradient(100deg,#ad1b86,#7830d3)}
      #statsPage .statsLeaderGrid{display:block!important}#statsPage .statsLeaderCard{display:none!important;min-height:0!important;height:auto!important;border-radius:16px!important;overflow:hidden!important}#statsPage .statsLeaderCard.fmMobileStatActive{display:block!important}
      #statsPage .statsLeaderCard>div[id]{max-height:none!important;height:auto!important;padding:6px 9px 12px!important}.statsCardHead{min-height:48px!important;padding:10px 12px!important}.statsCardHead h3{font-size:14px!important}
      #statsPage .statRow{min-height:47px!important;padding:5px 2px!important}.statRow .nm{font-size:10px!important}.statRow .sub{font-size:7px!important}.statRow>span:last-child{font-size:9px!important}
      #statsPage .statsBottom{display:flex!important;flex-direction:column!important;gap:9px!important}.statsInsights,.statsHighlights{border-radius:16px!important}.seasonInsightGrid,#statsInsights{display:flex!important;flex-direction:column!important;gap:8px!important;height:auto!important;padding:9px!important}.insightCard{min-height:155px!important}.statsHighlights{min-height:0!important}#statsHighlights{height:auto!important;padding:8px 11px!important}.highlightRow{min-height:45px!important}

      /* Rules are readable accordions on a phone. */
      #rulesPage .rulesConceptGrid{display:flex!important;flex-direction:column!important;gap:9px!important}#rulesPage .ruleConcept{height:auto!important;min-height:0!important;padding:0!important;border-radius:15px!important;overflow:hidden!important}
      #rulesPage .ruleTitle{position:relative!important;min-height:66px!important;margin:0!important;padding:11px 42px 11px 11px!important;align-items:center!important;cursor:pointer!important}.ruleTitle:after{content:'+';position:absolute;right:14px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:27px;height:27px;border-radius:50%;color:#fff;background:#35185c;font-size:18px}.ruleConcept.fmMobileExpanded>.ruleTitle:after{content:'−'}
      #rulesPage .ruleTitle>span{width:28px!important;height:28px!important;flex-basis:28px!important;font-size:12px!important}.ruleTitle h2{font-size:15px!important}.ruleTitle p{font-size:9px!important;line-height:1.35!important}
      #rulesPage .ruleConcept:not(.fmMobileExpanded)>:not(.ruleTitle){display:none!important}#rulesPage .ruleConcept.fmMobileExpanded>:not(.ruleTitle){margin-left:10px!important;margin-right:10px!important}#rulesPage .ruleConcept.fmMobileExpanded>:last-child{margin-bottom:10px!important}
      #rulesPage .ruleScoringTop,#rulesPage .ruleTwin,#rulesPage .ruleThirds,#rulesPage .ruleFour{display:flex!important;flex-direction:column!important;gap:8px!important}.ruleMini,.ruleStrip{min-height:0!important;padding:11px!important}.ruleMini b,.ruleStrip b{font-size:11px!important}.ruleMini p,.ruleStrip p,.ruleInfo{font-size:10.5px!important;line-height:1.5!important}.ruleGoalRows{font-size:10px!important}.rulesFooter{font-size:8px!important}

      /* Settings and player interactions are true full-width sheets. */
      #fmSettingsModal{align-items:end!important;padding:0!important}#fmSettingsCard{width:100vw!important;max-height:92dvh!important;margin:0!important;padding:19px 14px calc(18px + env(safe-area-inset-bottom))!important;border-radius:22px 22px 0 0!important;overflow-y:auto!important;box-sizing:border-box!important}.fmSetIdentity,.fmSetMeta{grid-template-columns:1fr!important}.fmSetIdentity input,.fmSetRow input{height:44px!important;font-size:12px!important}.fmSetActions{display:grid!important;grid-template-columns:1fr 1fr!important}.fmSetBtn{min-height:42px!important}
      .playerDrawer,.drawer{inset:0!important;width:100vw!important;height:100dvh!important;max-height:none!important;border-radius:0!important}.drawerBody{padding-bottom:calc(100px + env(safe-area-inset-bottom))!important}.drawerSignalGrid{grid-template-columns:repeat(2,1fr)!important}.drawerSignalGrid>div{min-height:55px!important}.compareModal,.modal{align-items:flex-end!important}.compareBox,.modalBox{width:100vw!important;max-width:none!important;max-height:94dvh!important;margin:0!important;border-radius:22px 22px 0 0!important}.compareMetric{grid-template-columns:minmax(0,1fr) 82px minmax(0,1fr)!important}
    }
    @media(max-width:430px){
      #fmMobileBrand{font-size:16px}.top h1{font-size:22px!important}.top .profile,.top .account,.top .managerPill{max-width:48%!important;transform:scale(.72)!important}
      .pitchCard .pchip{width:min(18.2vw,70px)!important}.pitchCard .shirt{width:32px!important;height:34px!important}.pitchCard .pchip b{font-size:8px!important}.pitchCard .pchip span{font-size:7px!important}
      #transfersPage .pitchCard>.cardh{align-items:flex-start!important}#transfersPage #autoFill{font-size:9px!important}
      #fixturesPage .fixtureHead{grid-template-columns:minmax(0,1fr) 24px 58px 24px minmax(0,1fr) 12px!important}.fixtureTeam{font-size:8.3px!important}
    }
  `;
  function title(){
    const active=document.querySelector('.page.active');
    return active?.querySelector('.top h1')?.textContent?.trim()||active?.querySelector('h1,h2')?.textContent?.trim()||'FM Fantasy';
  }
  function close(){document.body.classList.remove('fmMobileOpen');document.getElementById('fmMobileMenu')?.setAttribute('aria-expanded','false')}
  function activePage(){return document.querySelector('.page.active')?.id?.replace(/Page$/,'')||''}
  function updateTitle(){const el=document.getElementById('fmMobileTitle');if(el)el.textContent=title();const page=activePage(),primary=new Set(['news','team','transfers','leagues']);document.querySelectorAll('.fmMobileNavBtn').forEach(b=>b.classList.toggle('active',b.dataset.mobilePage===(primary.has(page)?page:'more')))}
  function openPage(page){
    const selectors=[`.sidebar [data-page="${page}"]`,`.sidebar [data-go="${page}"]`,`.sidebar button[data-target="${page}"]`];let button=null;
    for(const selector of selectors){button=document.querySelector(selector);if(button)break}
    if(!button){const label={news:'News',team:'My Team',transfers:'Transfers',leagues:'Leagues'}[page];button=[...document.querySelectorAll('.sidebar button')].find(x=>x.textContent.trim()===label)}
    if(button){button.click();close();requestAnimationFrame(()=>{updateTitle();enhanceMobileViews()})}
  }
  function ensureBottomNav(){
    if(document.getElementById('fmMobileNav'))return;const nav=document.createElement('nav');nav.id='fmMobileNav';nav.setAttribute('aria-label','Primary');
    const items=[['news','▤','News'],['team','♙','Team'],['transfers','⇄','Transfers'],['leagues','♜','Leagues'],['more','•••','More']];nav.innerHTML=items.map(([page,icon,label])=>`<button type="button" class="fmMobileNavBtn" data-mobile-page="${page}"><i>${icon}</i><span>${label}</span></button>`).join('');
    nav.addEventListener('click',event=>{const button=event.target.closest('.fmMobileNavBtn');if(!button)return;const page=button.dataset.mobilePage;if(page==='more'){const open=document.body.classList.toggle('fmMobileOpen');document.getElementById('fmMobileMenu')?.setAttribute('aria-expanded',String(open));return}openPage(page)});document.body.appendChild(nav)
  }
  let mobileStatIndex=0;
  function ensureStatsTabs(){
    const grid=document.querySelector('#statsPage .statsLeaderGrid');if(!grid)return;const cards=[...grid.children].filter(x=>x.classList.contains('statsLeaderCard'));if(!cards.length)return;
    let tabs=document.querySelector('#statsPage .fmMobileStatTabs');if(!tabs){tabs=document.createElement('div');tabs.className='fmMobileStatTabs';grid.parentElement.insertBefore(tabs,grid)}
    const labels=cards.map((card,index)=>card.querySelector('.statsCardHead h3,.statsCardHead b,h3')?.textContent?.trim()||['Points','Goals','Assists','Value'][index]||`Table ${index+1}`);
    if(tabs.children.length!==cards.length||tabs.dataset.labels!==labels.join('|')){tabs.dataset.labels=labels.join('|');tabs.innerHTML=labels.map((label,index)=>`<button type="button" class="fmMobileStatTab" data-stat-index="${index}">${label}</button>`).join('');tabs.onclick=event=>{const button=event.target.closest('[data-stat-index]');if(!button)return;mobileStatIndex=Number(button.dataset.statIndex)||0;ensureStatsTabs()}}
    mobileStatIndex=Math.min(mobileStatIndex,cards.length-1);cards.forEach((card,index)=>card.classList.toggle('fmMobileStatActive',index===mobileStatIndex));[...tabs.children].forEach((button,index)=>{button.classList.toggle('active',index===mobileStatIndex);button.setAttribute('aria-pressed',String(index===mobileStatIndex))})
  }
  function ensureRulesAccordions(){
    const rules=[...document.querySelectorAll('#rulesPage .ruleConcept')];rules.forEach((rule,index)=>{const head=rule.querySelector('.ruleTitle');if(!head)return;if(!rule.dataset.fmMobileRule){rule.dataset.fmMobileRule='1';head.tabIndex=0;head.setAttribute('role','button');head.addEventListener('click',()=>rule.classList.toggle('fmMobileExpanded'));head.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();rule.classList.toggle('fmMobileExpanded')}})}if(index===0&&!rules.some(x=>x.classList.contains('fmMobileExpanded')))rule.classList.add('fmMobileExpanded')})
  }
  function ensureFixtureFilter(){
    const head=document.querySelector('#fixturesPage .fixtureListHead');if(!head||document.getElementById('fmFixtureFilterToggle'))return;const button=document.createElement('button');button.id='fmFixtureFilterToggle';button.type='button';button.textContent='Filters';button.addEventListener('click',()=>{const open=document.body.classList.toggle('fmMobileFixtureFiltersOpen');button.textContent=open?'Hide filters':'Filters'});head.appendChild(button)
  }
  let enhanceQueued=0;
  function enhanceMobileViews(){if(innerWidth>900)return;cancelAnimationFrame(enhanceQueued);enhanceQueued=requestAnimationFrame(()=>{ensureBottomNav();ensureStatsTabs();ensureRulesAccordions();ensureFixtureFilter();updateTitle()})}
  let fitTimer=0;
  function fitPitches(){if(innerWidth>900)return;for(const wrap of document.querySelectorAll('.pitchScroll')){wrap.style.removeProperty('height');wrap.style.removeProperty('min-height')}for(const pitch of document.querySelectorAll('.pitch'))pitch.style.removeProperty('--fm-mobile-pitch-scale')}
  function queueFit(){clearTimeout(fitTimer);fitTimer=setTimeout(()=>{fitPitches();enhanceMobileViews()},40)}
  function boot(){
    if(document.getElementById('fmMobileStyles'))return;
    const style=document.createElement('style');style.id='fmMobileStyles';style.textContent=css;document.head.appendChild(style);
    const bar=document.createElement('header');bar.id='fmMobileBar';bar.innerHTML='<button id="fmMobileMenu" type="button" aria-label="Open navigation" aria-expanded="false">☰</button><div id="fmMobileBrand">FM <span class="fmMobileBrandAccent">Fantasy</span></div><div id="fmMobileTitle"></div>';
    const shade=document.createElement('div');shade.id='fmMobileBackdrop';shade.setAttribute('aria-hidden','true');
    document.body.append(bar,shade);
    bar.querySelector('#fmMobileMenu').addEventListener('click',()=>{const open=document.body.classList.toggle('fmMobileOpen');bar.querySelector('#fmMobileMenu').setAttribute('aria-expanded',String(open))});
    shade.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
    document.querySelector('.sidebar')?.addEventListener('click',e=>{if(e.target.closest('button')){setTimeout(()=>{close();updateTitle()},0)}});
    new MutationObserver(()=>{updateTitle();queueFit()}).observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});
    new MutationObserver(queueFit).observe(document.body,{subtree:true,childList:true});
    addEventListener('resize',queueFit,{passive:true});addEventListener('orientationchange',queueFit,{passive:true});
    const manifest=document.createElement('link');manifest.rel='manifest';manifest.href='./manifest.webmanifest?v=1';document.head.appendChild(manifest);
    for(const [name,content] of [['theme-color','#170728'],['apple-mobile-web-app-capable','yes'],['apple-mobile-web-app-status-bar-style','black-translucent'],['apple-mobile-web-app-title','FM Fantasy']]){if(!document.querySelector(`meta[name="${name}"]`)){const m=document.createElement('meta');m.name=name;m.content=content;document.head.appendChild(m)}}
    if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js?v=2').catch(()=>{});
    ensureBottomNav();enhanceMobileViews();updateTitle();queueFit();setTimeout(()=>{fitPitches();enhanceMobileViews()},250);setTimeout(()=>{fitPitches();enhanceMobileViews()},900);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
