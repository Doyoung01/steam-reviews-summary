import {
  BrowserRouter as Router,
  Route,
  Routes,
  Outlet,
  useNavigate,
} from "react-router-dom";
import { useState } from "react";
import "./App.css";
import List from "./component/List";
import Game from "./component/Game";

const apiBaseUrl = "https://steam-reviews-summary.onrender.com";

function App() {
  let [name, setName] = useState("");
  let [load, setLoad] = useState(true);
  let [games, setGame] = useState([]);
  let [pos, setPos] = useState("");
  let [neg, setNeg] = useState("");

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <Main
              setName={setName}
              name={name}
              setLoad={setLoad}
              setGame={setGame}
            />
          }
        >
          <Route path="/" element={<MainOutlet />} />
          <Route
            path="/game-list"
            element={
              <List
                load={load}
                games={games}
                setLoad={setLoad}
                setPos={setPos}
                setNeg={setNeg}
              />
            }
          />
          <Route
            path="/game"
            element={<Game load={load} neg={neg} pos={pos} />}
          />
        </Route>
      </Routes>
    </Router>
  );
}

function Main(props) {
  let nav = useNavigate();

  return (
    <div>
      <section className="steam-section">
        <h1 className="cursor-pointer" onClick={() => nav("/")}>
          Steam Review Summary
        </h1>
      </section>
      <div className="input-group mb-3">
        <input
          id="text"
          type="text"
          className="form-control"
          aria-label="Recipient's username"
          aria-describedby="button-addon2"
          placeholder="영어 이름이나 Steam URL을 입력하세요."
          onChange={(e) => {
            props.setName(e.target.value);
            console.log(props.name);
          }}
        />
        <button
          className="btn btn-outline-secondary"
          type="button"
          id="button-addon2"
          name="btn"
          onClick={() => {
            nav("/game-list");
            fetchGameData(props.name, props.setLoad, props.setGame);
          }}
        >
          검색
        </button>
      </div>
      <Outlet />
    </div>
  );
}

function MainOutlet() {
  return (
    <p>
      영어 게임 이름이나 Steam URL을 검색하시면 혐오 표현이 필터링된 리뷰 요약을
      보실 수 있습니다.
    </p>
  );
}

const fetchGameData = async (query, setLoad, setGame) => {
  let result = [];

  setLoad(true);

  if (query.startsWith("http")) {
    try {
      const response = await fetch(
        `${apiBaseUrl}/search_game_by_link?game_url=${query}`
      );
      const data = await response.json();

      if (response.ok) {
        result = [[data.query, data.results]]; // app_id와 게임 이름을 배열로 저장
      } else {
        console.error("Error:", data.detail);
        result = [["", "게임을 찾을 수 없습니다."]];
      }
    } catch (error) {
      console.error("Error fetching game data:", error);
      result = [["", "게임 데이터를 가져오는 중 오류가 발생했습니다."]];
    }
  } else {
    try {
      const response = await fetch(`${apiBaseUrl}/search_game?query=${query}`);
      const data = await response.json();

      if (response.ok) {
        result = data.results.map((game) => [game.appid, game.name]);
      } else {
        console.error("Error:", data.detail);
        result = [["", "게임을 찾을 수 없습니다."]];
      }
    } catch (error) {
      console.error("Error fetching game data:", error);
      result = [["", "게임 데이터를 가져오는 중 오류가 발생했습니다."]];
    }
  }

  setGame(result);
  setLoad(false);
};

export default App;
