import matplotlib.pyplot as plt
from rag_eval4 import amazon_db, youtube_db, specs_db, idea_to_query, retrieve_ranked_products, gt_to_products, normalize_product, detect_category, precision_at_k_products, recall_at_k_products
import json
import math
from rag_pipeline1 import (
    retrieve_products,
    group_by_product,
    build_product_profiles,
    rank_products
)

'''#Precision-Recall Curve
def compute_precision_recall_curve(ranked_products, gt_products, max_k=20):
    ks = list(range(1, max_k + 1))
    gt_set = set(gt_products.keys())
    precision_values = []
    recall_values = []
    hits=0

    for k in ks:
        if (k-1)<len(ranked_products) and ranked_products[k-1] in gt_set:
            hits+=1
        
        # precision = precision_at_k_products(ranked_products, gt_products, k)
        # recall = recall_at_k_products(ranked_products, gt_products, k)
        # precision_values.append(precision)
        # recall_values.append(recall)

        precision=hits/k
        recall=hits/len(gt_set) if gt_set else 0
        if recall>1:
            print("Error: Recall exceeds 1")
            print("GT:",gt_products)
            print("Ranked:", ranked_products[:k])
            exit(1)

        precision_values.append(precision)
        recall_values.append(recall)

    return ks, precision_values, recall_values

def compute_average_pr_curve(ideas, ideas_dict, max_k=20):
    ks = list(range(1, max_k + 1))
    avg_precision_values = [0.0] * max_k
    avg_recall_values = [0.0] * max_k
    num_ideas=10

    for idea_file in ideas:
        print(f"\nProcessing: {idea_file}")

        idea_json=json.load(open(idea_file,encoding="utf-8"))
        ground_truth=json.load(open(ideas_dict[idea_file],encoding="utf-8"))
        query=idea_to_query(idea_json)
        category = detect_category(idea_json)
        constraints = idea_json.get("constraints", {})

        ranked=retrieve_ranked_products(query, category, constraints)
        #ranked_products = [normalize_product(product) for product, _, _ in ranked]
        ranked_products = list(dict.fromkeys(normalize_product(product) for product, _, _ in ranked))
        gt_products = gt_to_products(ground_truth)

        ks, precision_vals, recall_vals=compute_precision_recall_curve(ranked_products, gt_products, max_k)
        for i in range(max_k):
            avg_precision_values[i] += precision_vals[i]
            avg_recall_values[i] += recall_vals[i]
    
    avg_precision=[val / num_ideas for val in avg_precision_values]
    avg_recall=[val / num_ideas for val in avg_recall_values]
    return ks, avg_precision, avg_recall

def plot_precision_recall_curve(ks, avg_precision, avg_recall):
    plt.figure()
    plt.plot(ks, avg_precision, label='Precision', marker='o')
    plt.plot(ks, avg_recall, label='Recall', marker='o')
    plt.xlabel('K')
    plt.ylabel('Value')
    plt.title('Precision-Recall Curve')
    plt.legend()
    plt.grid()
    plt.show()

def run_pr_curve_evaluation(idea_json, ground_truth):
    query=idea_to_query(idea_json)
    category = detect_category(idea_json)
    constraints = idea_json.get("constraints", {})
    
    ranked=retrieve_ranked_products(query, category, constraints)
    #ranked_products = [normalize_product(product) for product, _, _ in ranked]
    ranked_products = list(dict.fromkeys(normalize_product(product) for product, _, _ in ranked))
    gt_products = gt_to_products(ground_truth)

    ks, precision_values, recall_values = compute_precision_recall_curve(ranked_products, gt_products)
    plot_precision_recall_curve(ks, precision_values, recall_values)

#Driver Code
if __name__ == "__main__":
    ideas=[]
    ideas_dict={}

    #for ctr in range(1,11):
    #     idea_file= f"./Ideas/idea{ctr}.json"
    #     ground_truth_file=f"./ground_truth/idea{ctr}.json"

    #     ideas_dict[idea_file]=ground_truth_file
    #     ideas.append(idea_file)
    
    ideas_dict = {
    "./Ideas/idea1.json": "./ground_truth/idea1.json",
    "./Ideas/idea2.json": "./ground_truth/idea2.json",
    "./Ideas/idea3.json": "./ground_truth/idea3.json",
    "./Ideas/idea4.json": "./ground_truth/idea4.json",
    "./Ideas/idea5.json": "./ground_truth/idea5.json",
    "./Ideas/idea6.json": "./ground_truth/idea6.json",
    "./Ideas/idea7.json": "./ground_truth/idea7.json",
    "./Ideas/idea8.json": "./ground_truth/idea8.json",
    "./Ideas/idea9.json": "./ground_truth/idea9.json",
    "./Ideas/idea10.json": "./ground_truth/idea10.json"
    }

    ideas = list(ideas_dict.keys())
    
    #Find average of all 10 ideas
    ks, avg_precision, avg_recall = compute_average_pr_curve(ideas, ideas_dict)

    print("\nAverage Precision:", avg_precision)
    print("Average Recall:", avg_recall)

    plot_precision_recall_curve(ks, avg_precision, avg_recall)

#NDCG@k curve
def compute_ndcg_curve(ranked_products, gt_products, max_k=20):
    ks = list(range(1, max_k + 1))
    ndcg_values = []

    for k in ks:
        dcg = 0
        for i, product in enumerate(ranked_products[:k]):
            rel = gt_products.get(product, 0)
            dcg += (2**rel - 1) / math.log2(i + 2)

        # Ideal DCG
        ideal_rels = sorted(gt_products.values(), reverse=True)[:k]
        idcg = 0
        for i, rel in enumerate(ideal_rels):
            idcg += (2**rel - 1) / math.log2(i + 2)

        ndcg = dcg / idcg if idcg > 0 else 0
        ndcg_values.append(ndcg)

    return ks, ndcg_values

def compute_average_ndcg_curve(ideas, ideas_dict, max_k=20):
    ks = list(range(1, max_k + 1))
    avg_ndcg = [0.0] * max_k
    num_ideas = len(ideas)

    for idea_file in ideas:
        print(f"\nProcessing: {idea_file}")

        idea_json = json.load(open(idea_file, encoding="utf-8"))
        ground_truth = json.load(open(ideas_dict[idea_file], encoding="utf-8"))

        query = idea_to_query(idea_json)
        category = detect_category(idea_json)
        constraints = idea_json.get("constraints", {})

        ranked = retrieve_ranked_products(query, category, constraints)

        # 🔥 IMPORTANT: normalize + deduplicate
        ranked_products = list(dict.fromkeys(
            normalize_product(product) for product, _, _ in ranked
        ))

        gt_products = gt_to_products(ground_truth)

        _, ndcg_vals = compute_ndcg_curve(ranked_products, gt_products, max_k)

        for i in range(max_k):
            avg_ndcg[i] += ndcg_vals[i]

    avg_ndcg = [val / num_ideas for val in avg_ndcg]
    return ks, avg_ndcg

def plot_ndcg_curve(ks, ndcg_values):
    plt.figure()
    plt.plot(ks, ndcg_values, marker='o')
    plt.xlabel("K")
    plt.ylabel("NDCG")
    plt.title("NDCG@K Curve")
    plt.grid()
    plt.show()

if __name__ == "__main__":
    ideas_dict = {
        "./Ideas/idea1.json": "./ground_truth/idea1.json",
        "./Ideas/idea2.json": "./ground_truth/idea2.json",
        "./Ideas/idea3.json": "./ground_truth/idea3.json",
        "./Ideas/idea4.json": "./ground_truth/idea4.json",
        "./Ideas/idea5.json": "./ground_truth/idea5.json",
        "./Ideas/idea6.json": "./ground_truth/idea6.json",
        "./Ideas/idea7.json": "./ground_truth/idea7.json",
        "./Ideas/idea8.json": "./ground_truth/idea8.json",
        "./Ideas/idea9.json": "./ground_truth/idea9.json",
        "./Ideas/idea10.json": "./ground_truth/idea10.json"
    }

    ideas = list(ideas_dict.keys())
    ks, avg_ndcg = compute_average_ndcg_curve(ideas, ideas_dict)
    print("\nAverage NDCG:", avg_ndcg)
    plot_ndcg_curve(ks, avg_ndcg)'''

#Similarity Score Graphs
def get_similarity_scores(query, db, k=20):
    results=db.similarity_search_with_score(f"query: {query}", k=k)
    scores=[score for _, score in results]
    return scores

def plot_similarity_curves(amazon_scores, youtube_scores, specs_scores):
    # amazon_scores=get_similarity_scores(query, amazon_db)
    # youtube_scores=get_similarity_scores(query, youtube_db)
    # specs_scores=get_similarity_scores(query, specs_db)
    #hybrid_scores=get_hybrid_scores_from_docs(query, category, constraints)

    plt.figure()
    plt.plot(amazon_scores, marker="o", label="Amazon Reviews")
    plt.plot(youtube_scores, marker='o', label='YouTube Reviews')
    plt.plot(specs_scores, marker='o', label='Product Specs')
    #plt.plot(hybrid_scores, marker='o', label="Hybrid")

    plt.xlabel("Rank")
    plt.ylabel("Similarity Score")
    plt.title("Source-wise Rank-wise Similarity Scores")
    plt.legend()
    plt.show()

def plot_similarity_curves1(amazon_scores, youtube_scores, specs_scores):
    ks = list(range(1, len(amazon_scores) + 1))

    plt.figure()
    plt.plot(ks, amazon_scores, marker="o", label="Amazon")
    plt.plot(ks, youtube_scores, marker='o', label='YouTube')
    plt.plot(ks, specs_scores, marker='o', label='Specs')

    plt.xlabel("Rank")
    plt.ylabel("Average Similarity Score")
    plt.title("Source-wise Retrieval Scores (Rank vs Similarity)")
    plt.legend()
    plt.grid()
    plt.show()

def plot_hybrid_scores1(scores):
    ks = list(range(1, len(scores) + 1))

    plt.figure()
    plt.plot(ks, scores, marker='o', color='red')

    plt.xlabel("Rank")
    plt.ylabel("Hybrid Score")
    plt.title("Hybrid Model Ranking Scores (Final Product Ranking)")
    plt.grid()
    plt.show()

def plot_hybrid_scores(scores):
    #scores=get_hybrid_scores_from_docs(a_docs, y_docs, s_docs, constraints)
    
    plt.figure()
    plt.plot(scores, marker='o')
    plt.xlabel("Rank")
    plt.ylabel("Final Score")
    plt.title("Hybrid Final Ranking Scores")
    plt.show()

def get_similarity_scores_from_docs(docs):
    return [score for _, score in docs]

def get_hybrid_scores_from_docs(a_docs, y_docs, s_docs, constraints):
    grouped = group_by_product(a_docs, y_docs, s_docs)
    profiles = build_product_profiles(grouped)
    ranked = rank_products(profiles, constraints)

    scores = [score for _, _, score in ranked]
    return scores

def normalize(scores):
    min_s = min(scores)
    max_s = max(scores)
    if max_s - min_s == 0:
        return [0 for _ in scores]
    return [(s - min_s) / (max_s - min_s) for s in scores]

def compute_average_similarity_curve(ideas, max_k=20):
    avg_amazon = [0.0] * max_k
    avg_youtube = [0.0] * max_k
    avg_specs = [0.0] * max_k
    avg_hybrid = [0.0] * max_k

    num_ideas=10

    count_amazon = [0]*max_k
    count_youtube = [0]*max_k
    count_specs = [0]*max_k
    count_hybrid = [0]*max_k

    for idea_file in ideas:
        print(f"\nProcessing: {idea_file}")

        idea_json = json.load(open(idea_file, encoding="utf-8"))
        query = idea_to_query(idea_json)
        category = detect_category(idea_json)
        constraints = idea_json.get("constraints", {})

        a_docs, y_docs, s_docs=retrieve_products(query, category)

        amazon_scores = get_similarity_scores_from_docs(a_docs)
        youtube_scores = get_similarity_scores_from_docs(y_docs)
        specs_scores = get_similarity_scores_from_docs(s_docs)
        hybrid_scores = get_hybrid_scores_from_docs(a_docs, y_docs, s_docs, constraints)[:max_k]

        for i in range(max_k):
            if i < len(amazon_scores):
                avg_amazon[i] += amazon_scores[i]
                count_amazon[i] += 1

            if i < len(youtube_scores):
                avg_youtube[i] += youtube_scores[i]
                count_youtube[i] += 1

            if i < len(specs_scores):
                avg_specs[i] += specs_scores[i]
                count_specs[i] += 1

            if i < len(hybrid_scores):
                avg_hybrid[i] += hybrid_scores[i]
                count_hybrid[i] += 1

    avg_amazon = [avg_amazon[i]/count_amazon[i] if count_amazon[i] else 0 for i in range(max_k)]
    avg_youtube = [avg_youtube[i]/count_youtube[i] if count_youtube[i] else 0 for i in range(max_k)]
    avg_specs = [avg_specs[i]/count_specs[i] if count_specs[i] else 0 for i in range(max_k)]
    avg_hybrid = [avg_hybrid[i]/count_hybrid[i] if count_hybrid[i] else 0 for i in range(max_k)]

    return avg_amazon, avg_youtube, avg_specs, avg_hybrid

def plot_average_similarity_curves(avg_amazon, avg_youtube, avg_specs):
    ks = list(range(1, len(avg_amazon) + 1))

    plt.figure()
    plt.plot(ks, avg_amazon, marker='o', label="Amazon")
    plt.plot(ks, avg_youtube, marker='o', label="YouTube")
    plt.plot(ks, avg_specs, marker='o', label="Specs")
    #plt.plot(ks, avg_hybrid, marker='o', label="Hybrid")

    plt.xlabel("Rank")
    plt.ylabel("Average Similarity Score")
    plt.title("Source-wise Rank-wise Similarity Scores")
    plt.legend()
    plt.grid()
    plt.show()

def plot_average_similarity_curves_norm(avg_amazon, avg_youtube, avg_specs, avg_hybrid):
    ks = list(range(1, len(avg_amazon) + 1))

    plt.figure()
    plt.plot(ks, avg_amazon, marker='o', label="Amazon")
    plt.plot(ks, avg_youtube, marker='o', label="YouTube")
    plt.plot(ks, avg_specs, marker='o', label="Specs")
    plt.plot(ks, avg_hybrid, marker='o', label="Hybrid")

    plt.xlabel("Rank")
    plt.ylabel("Average Normalized Score")
    plt.title("Normalized Rank-wise Score Comparison: Amazon, YouTube, Specs vs Hybrid Model")
    plt.legend()
    plt.grid()
    plt.show()

#Driver Code
if __name__ == "__main__":
    ideas_dict = {
        "./Ideas/idea1.json": "./ground_truth/idea1.json",
        "./Ideas/idea2.json": "./ground_truth/idea2.json",
        "./Ideas/idea3.json": "./ground_truth/idea3.json",
        "./Ideas/idea4.json": "./ground_truth/idea4.json",
        "./Ideas/idea5.json": "./ground_truth/idea5.json",
        "./Ideas/idea6.json": "./ground_truth/idea6.json",
        "./Ideas/idea7.json": "./ground_truth/idea7.json",
        "./Ideas/idea8.json": "./ground_truth/idea8.json",
        "./Ideas/idea9.json": "./ground_truth/idea9.json",
        "./Ideas/idea10.json": "./ground_truth/idea10.json"
    }

    ideas = list(ideas_dict.keys())

    avg_amazon, avg_youtube, avg_specs, avg_hybrid = compute_average_similarity_curve(ideas)

    # plot_average_similarity_curves(avg_amazon, avg_youtube, avg_specs)
    # print(avg_amazon[:5])
    # print(avg_hybrid[:5])

    # avg_amazon_norm=normalize(avg_amazon)
    # avg_youtube_norm=normalize(avg_youtube)
    # avg_specs_norm=normalize(avg_specs)
    # avg_hybrid_norm=normalize(avg_hybrid)

    # plot_average_similarity_curves_norm(avg_amazon_norm, avg_youtube_norm, avg_specs_norm, avg_hybrid_norm)

    plot_similarity_curves1(avg_amazon, avg_youtube, avg_specs)
    plot_hybrid_scores1(avg_hybrid)
        

