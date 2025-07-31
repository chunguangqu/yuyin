import re

class LocalRAG:
    def __init__(self, txt_path):
        self.qa_pairs = self.load_qa(txt_path)

    def load_qa(self, path):
        qa_pairs = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'question：(.+?)answer：(.+)', line.strip())
                if m:
                    qa_pairs.append((m.group(1).strip(), m.group(2).strip()))
        return qa_pairs

    def simple_similarity(self, q1, q2):
        # 计算两个字符串的最长公共子串长度占比
        def lcs(a, b):
            dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
            maxlen = 0
            for i in range(1, len(a)+1):
                for j in range(1, len(b)+1):
                    if a[i-1] == b[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                        maxlen = max(maxlen, dp[i][j])
            return maxlen
        lcs_len = lcs(q1, q2)
        return lcs_len / max(len(q1), len(q2), 1)

    def search(self, query, threshold=0.5):
        best_score = 0
        best_answer = None
        for q, a in self.qa_pairs:
            score = self.simple_similarity(query, q)
            if score > best_score:
                best_score = score
                best_answer = a
        if best_score >= threshold:
            return best_answer
        else:
            return None