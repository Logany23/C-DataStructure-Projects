//核心算法逻辑实现
#include "huffman.h"

// 创建新节点
Node* createNode(unsigned char data, unsigned freq) {
    Node* newNode = (Node*)malloc(sizeof(Node));
    if (!newNode) return NULL;
    newNode->data = data;
    newNode->freq = freq;
    newNode->left = newNode->right = NULL;
    return newNode;
}

// 统计文件字符频率
void countFrequency(const char* filename, unsigned f[256]) {
    FILE* file = fopen(filename, "rb"); // 以二进制只读方式打开
    if (!file) {
        printf("无法打开文件！\n");
        return;
    }

    // 初始化频率数组为 0
    for (int i = 0; i < 256; i++) f[i] = 0;

    int ch;
    while ((ch = fgetc(file)) != EOF) {
        f[(unsigned char)ch]++; // 对应的字符频率 +1
    }

    fclose(file);
}