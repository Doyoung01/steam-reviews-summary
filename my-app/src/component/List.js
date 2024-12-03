import React from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";

function List(props) {
  let nav = useNavigate();

  return props.load ? (
    <h3
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      게임을 검색 중입니다...
    </h3>
  ) : (
    <table className="table table-striped table-hover">
      <thead>
        <tr>
          <th>게임명</th>
          <th>APP ID</th>
        </tr>
      </thead>
      <tbody>
        {props.games.map((e, idx) => {
          console.log(e);
          return e[1] === "게임을 찾을 수 없습니다." ? (
            <tr key={idx}>
              <td>{e[1]}</td>
              <td>{e[0]}</td>
            </tr>
          ) : (
            <tr
              key={idx}
              className="cursor-pointer"
              onClick={() => {
                nav("/game");
                fetchReviewData(
                  e[0],
                  props.setLoad,
                  props.setPos,
                  props.setNeg
                );
              }}
            >
              <td>{e[1]}</td>
              <td>{e[0]}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

const fetchReviewData = async (query, setLoad, setPos, setNeg) => {
  setLoad(true);

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/reviews?app_id=${query}`
    );
    const data = await response.json();
    if (response.ok) {
      setPos(data.positive_summary);
      setNeg(data.negative_summary);
    } else {
      console.error("Error:", data.detail);
    }
  } catch (error) {
    console.error("Error fetching reviews:", error);
  }

  setLoad(false);
};

export default List;
