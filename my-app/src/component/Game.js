import React from "react";

function Info(props) {
  return props.load ? (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      <h3>결과 출력 중...</h3>
      <h3>약 1분 정도 소요될 수 있습니다...</h3>
      <h7>리뷰 읽는 거... 은근 재밌어요...</h7>
      <h7>설문조사... 꼭 부탁 드립니다...</h7>
      <img
        src="/bingbing.gif"
        alt="Bing Bing GIF"
        style={{ width: "300px", height: "auto" }}
      />
    </div>
  ) : (
    <div>
      <section className="positive-section">
        <h3>🥰긍정적인 리뷰🥰</h3>
        <p>{props.pos || "긍정적인 리뷰가 없습니다."}</p>
      </section>
      <section className="negative-section">
        <h3>🤨부정적인 리뷰🤨</h3>
        <p>{props.neg || "부정적인 리뷰가 없습니다."}</p>
      </section>
    </div>
  );
}

export default Info;
